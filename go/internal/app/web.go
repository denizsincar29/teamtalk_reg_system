package app

import (
	"embed"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"
)

//go:embed embed/*.html
var embedHTML embed.FS

var pageTemplates = template.Must(template.ParseFS(embedHTML, "embed/*.html"))

// Server wires the HTTP layer: public registration pages, the admin session,
// and the JSON API consumed by the dashboard. Session cookies only record
// "this tab is logged in"; the source of truth for admins is the TeamTalk
// account list, checked at login time (AuthenticateAdmin).
type Server struct {
	cfg   Config
	svc   *Service
	sched *Scheduler

	mu       sync.Mutex
	sessions map[string]sessionRec
}

type sessionRec struct {
	user string
	exp  time.Time
}

func NewServer(cfg Config, svc *Service, sched *Scheduler) *Server {
	return &Server{
		cfg:      cfg,
		svc:      svc,
		sched:    sched,
		sessions: make(map[string]sessionRec),
	}
}

// Handler builds the router. Admin JSON/API routes live under /admin and are
// guarded by the session; public registration stays open.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()

	// Public.
	mux.HandleFunc("GET /{$}", s.pageIndex)
	mux.HandleFunc("POST /register", s.handleRegister)
	mux.HandleFunc("GET /download-tt/{username}/{password}", s.handleDownloadTT)
	mux.HandleFunc("GET /tturl", s.handleTTURL)
	mux.HandleFunc("GET /open", s.handleOpen)

	// Admin login/logout and the dashboard shell.
	mux.HandleFunc("GET /admin/login", s.pageLogin)
	mux.HandleFunc("POST /admin/login", s.login)
	mux.HandleFunc("GET /admin/logout", s.logout)
	mux.Handle("GET /admin", http.RedirectHandler("/admin/", http.StatusFound))
	mux.HandleFunc("GET /admin/", s.adminPage(s.pageDashboard))

	// Admin JSON API.
	api := func(fn http.HandlerFunc) http.HandlerFunc { return s.adminPage(fn) }
	mux.HandleFunc("GET /admin/api/overview", api(s.overview))
	mux.HandleFunc("GET /admin/api/status", api(s.apiStatus))
	mux.HandleFunc("POST /admin/api/status", api(s.apiSetStatus))
	mux.HandleFunc("GET /admin/api/accounts", api(s.apiAccounts))
	mux.HandleFunc("GET /admin/api/accounts/{username}/ttfile", api(s.apiAccountTTFile))
	mux.HandleFunc("GET /admin/api/accounts/{username}/tturl", api(s.apiAccountTTURL))
	mux.HandleFunc("POST /admin/api/accounts/{username}/ban", api(s.apiAccountBan))
	mux.HandleFunc("POST /admin/api/accounts/{username}/unban", api(s.apiAccountUnban))
	mux.HandleFunc("DELETE /admin/api/accounts/{username}", api(s.apiAccountDelete))
	mux.HandleFunc("GET /admin/api/users", api(s.apiUsers))
	mux.HandleFunc("GET /admin/api/channels", api(s.apiChannels))
	mux.HandleFunc("POST /admin/api/channels/join", api(s.apiChannelJoin))
	mux.HandleFunc("POST /admin/api/channels/leave", api(s.apiChannelLeave))
	mux.HandleFunc("GET /admin/api/messages", api(s.apiMessages))
	mux.HandleFunc("POST /admin/api/messages/clear", api(s.apiMessagesClear))
	mux.HandleFunc("GET /admin/api/messages/stream", api(s.apiMsgStream))
	mux.HandleFunc("GET /admin/api/events", api(s.apiEvents))
	mux.HandleFunc("POST /admin/api/events/clear", api(s.apiEventsClear))
	mux.HandleFunc("POST /admin/api/broadcast", api(s.apiBroadcast))
	mux.HandleFunc("POST /admin/api/send_message", api(s.apiSendMessage))
	mux.HandleFunc("POST /admin/api/send_channel_message", api(s.apiSendChannelMessage))
	mux.HandleFunc("POST /admin/api/kick", api(s.apiKick))
	mux.HandleFunc("POST /admin/api/ban", api(s.apiBan))
	mux.HandleFunc("POST /admin/api/ban_username", api(s.apiBanUsername))
	mux.HandleFunc("GET /admin/api/tasks", api(s.apiTasks))
	mux.HandleFunc("POST /admin/api/tasks", api(s.apiTaskCreate))
	mux.HandleFunc("PUT /admin/api/tasks/{id}", api(s.apiTaskUpdate))
	mux.HandleFunc("DELETE /admin/api/tasks/{id}", api(s.apiTaskDelete))
	mux.HandleFunc("POST /admin/api/tasks/{id}/toggle", api(s.apiTaskToggle))
	mux.HandleFunc("POST /admin/api/tasks/{id}/run", api(s.apiTaskRun))
	mux.HandleFunc("GET /admin/api/queue_offline_pm", api(s.apiQueue))
	mux.HandleFunc("POST /admin/api/queue_offline_pm", api(s.apiQueueAdd))
	mux.HandleFunc("DELETE /admin/api/queue_offline_pm/{username}", api(s.apiQueueClear))

	return logRequests(mux)
}

func logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		next.ServeHTTP(w, r)
	})
}

// ---- page rendering helpers ----

type viewData map[string]any

func (s *Server) render(w http.ResponseWriter, name string, data viewData) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := pageTemplates.ExecuteTemplate(w, name, data); err != nil {
		log.Printf("web: template %s: %v", name, err)
	}
}

// ---- session handling ----

const (
	sessionCookie = "admin_session"
	sessionTTL    = 30 * 24 * time.Hour
)

func (s *Server) newSession(user string) string {
	tok := randToken()
	s.mu.Lock()
	s.sessions[tok] = sessionRec{user: user, exp: time.Now().Add(sessionTTL)}
	s.sweepLocked()
	s.mu.Unlock()
	return tok
}

func (s *Server) sweepLocked() {
	now := time.Now()
	for k, v := range s.sessions {
		if now.After(v.exp) {
			delete(s.sessions, k)
		}
	}
}

// sessionUser validates the request cookie and, on success, slides the session
// expiry forward (30-day rolling session).
func (s *Server) sessionUser(r *http.Request) string {
	c, err := r.Cookie(sessionCookie)
	if err != nil {
		return ""
	}
	s.mu.Lock()
	rec, ok := s.sessions[c.Value]
	if ok {
		rec.exp = time.Now().Add(sessionTTL)
		s.sessions[c.Value] = rec
	}
	s.mu.Unlock()
	if !ok {
		return ""
	}
	return rec.user
}

// adminPage wraps a handler with the session guard: HTML pages that fail auth
// get redirected to the login form; JSON API calls get a 401.
func (s *Server) adminPage(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user := s.sessionUser(r)
		if user == "" {
			if strings.HasPrefix(r.URL.Path, "/admin/api/") {
				writeJSON(w, http.StatusUnauthorized, map[string]any{"error": "Not logged in"})
				return
			}
			http.Redirect(w, r, "/admin/login", http.StatusFound)
			return
		}
		next(w, r)
	}
}

// ---- public pages ----

func (s *Server) pageIndex(w http.ResponseWriter, r *http.Request) {
	s.render(w, "index.html", viewData{
		"Host":    s.cfg.PublicHost,
		"TcpPort": s.cfg.TCPPort,
		"UdpPort": s.cfg.UDPPort,
		"Error":   "",
	})
}

func (s *Server) pageLogin(w http.ResponseWriter, r *http.Request) {
	// Already logged in: straight to the dashboard.
	if s.sessionUser(r) != "" {
		http.Redirect(w, r, "/admin/", http.StatusFound)
		return
	}
	s.render(w, "login.html", viewData{"Error": ""})
}

func (s *Server) handleRegister(w http.ResponseWriter, r *http.Request) {
	fail := func(msg string) {
		s.render(w, "index.html", viewData{
			"Host": s.cfg.PublicHost, "TcpPort": s.cfg.TCPPort, "UdpPort": s.cfg.UDPPort, "Error": msg,
		})
	}
	username := strings.TrimSpace(r.FormValue("username"))
	password := r.FormValue("password")

	// Согласие — правовое основание обработки (152-ФЗ): без галочки аккаунт
	// не заводим, иначе подтвердить согласие будет нечем.
	if r.FormValue("consent") == "" {
		fail("Нужно согласие с политикой обработки персональных данных.")
		return
	}
	if !validUsername(username) {
		fail("Ник должен быть от 3 символов: латинские буквы, цифры и подчёркивание.")
		return
	}
	if len(password) < 4 {
		fail("Пароль должен быть не короче 4 символов.")
		return
	}
	exists, err := s.svc.CheckUserExists(username)
	if err != nil {
		fail("Сервер сейчас недоступен, попробуй позже.")
		return
	}
	if exists {
		fail("Аккаунт с таким ником уже существует.")
		return
	}
	if err := s.svc.CreateUser(username, password); err != nil {
		fail("Не удалось создать аккаунт: " + err.Error())
		return
	}

	s.render(w, "success.html", viewData{
		"Username":    username,
		"Password":    password,
		"Host":        s.cfg.PublicHost,
		"TcpPort":     s.cfg.TCPPort,
		"UdpPort":     s.cfg.UDPPort,
		"DownloadURL": "/download-tt/" + username + "/" + base64.RawURLEncoding.EncodeToString([]byte(password)),
		// template.URL: see handleOpen — without it the button gets "#ZgotmplZ"
		// and the freshly registered user has no working "connect now" link.
		"TTURL": template.URL(ttURL(s.cfg, username, password)),
	})
}

func validUsername(u string) bool {
	if len(u) < 3 || len(u) > 32 {
		return false
	}
	for i := 0; i < len(u); i++ {
		c := u[i]
		if !(c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9' || c == '_') {
			return false
		}
	}
	return true
}

func (s *Server) handleDownloadTT(w http.ResponseWriter, r *http.Request) {
	username := r.PathValue("username")
	raw := r.PathValue("password")
	pw, err := base64.RawURLEncoding.DecodeString(raw)
	if err != nil {
		// tolerate padded input from hand-crafted links
		pw, err = base64.URLEncoding.DecodeString(raw)
	}
	if err != nil || len(pw) == 0 {
		http.Error(w, "bad link", http.StatusBadRequest)
		return
	}
	ok, err := s.svc.CheckUserExists(username)
	if err != nil {
		http.Error(w, "server unavailable", http.StatusServiceUnavailable)
		return
	}
	if !ok {
		http.Error(w, "unknown user", http.StatusNotFound)
		return
	}
	body := ttFileXML(s.cfg, username, string(pw))
	w.Header().Set("Content-Type", "application/xml")
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%q", username+".tt"))
	_, _ = w.Write([]byte(body))
}

// handleTTURL turns a short https link into a tt:// address. Chat clients link
// only https URLs, so an invitation meant for a messenger is sent as
// https://<ShortHost>/tturl?u=<ник>&p=<base64 пароль> and the browser follows
// the redirect into the installed TeamTalk client.
//
// The handler is deliberately stateless: the account travels entirely in the
// query, so it answers even while the TeamTalk server is down, and it never
// looks accounts up — which would turn a public URL into a password oracle for
// anyone who guesses a username.
func (s *Server) handleTTURL(w http.ResponseWriter, r *http.Request) {
	username, password, ok := linkCredentials(r)
	if !ok {
		http.Error(w, "bad link", http.StatusBadRequest)
		return
	}
	http.Redirect(w, r, ttURL(s.cfg, username, password), http.StatusFound)
}

// handleOpen is the page a push notification taps into. A phone will not open
// a custom scheme from a notification, and it will not follow the redirect
// /tturl answers with either — Safari only says "cannot show URL". A link on a
// page is the user gesture the system wants, so the page offers the address as
// two buttons: the two known shapes of a tt:// address, since no client
// documents which one it accepts.
func (s *Server) handleOpen(w http.ResponseWriter, r *http.Request) {
	username, password, ok := linkCredentials(r)
	if !ok {
		http.Error(w, "bad link", http.StatusBadRequest)
		return
	}
	// template.URL is required here: html/template does not know the tt scheme
	// and would otherwise replace the href with "#ZgotmplZ". Both addresses are
	// built by ttURL/ttURLQuery from a validated username and a percent-encoded
	// password, so there is nothing to smuggle in.
	s.render(w, "open.html", viewData{
		"Username":     username,
		"LinkQuery":    template.URL(ttURLQuery(s.cfg, username, password)),
		"LinkUserInfo": template.URL(ttURL(s.cfg, username, password)),
	})
}

// linkCredentials reads the account out of ?u=<ник>&p=<base64 пароль> — the
// same stateless encoding the redirector uses, so neither handler has to look
// anything up (and neither can serve as a password oracle).
func linkCredentials(r *http.Request) (username, password string, ok bool) {
	username = strings.TrimSpace(r.URL.Query().Get("u"))
	raw := strings.TrimSpace(r.URL.Query().Get("p"))
	if !validLinkUsername(username) || raw == "" {
		return "", "", false
	}
	pw, err := base64.RawURLEncoding.DecodeString(raw)
	if err != nil {
		// tolerate padded input from hand-crafted links
		pw, err = base64.URLEncoding.DecodeString(raw)
	}
	if err != nil || len(pw) == 0 {
		return "", "", false
	}
	return username, string(pw), true
}

// validLinkUsername is the redirector's guard. It is looser than
// validUsername — accounts made straight on the TeamTalk server may carry dots
// or dashes — and only rejects names that cannot survive the redirect: empty,
// overlong, or holding control characters. ttURL percent-encodes the rest.
func validLinkUsername(u string) bool {
	if u == "" || len(u) > 64 {
		return false
	}
	for i := 0; i < len(u); i++ {
		if u[i] <= 0x20 || u[i] == 0x7f {
			return false
		}
	}
	return true
}

// ---- JSON helpers ----

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func okJSON(w http.ResponseWriter, extra map[string]any) {
	m := map[string]any{"ok": true}
	for k, v := range extra {
		m[k] = v
	}
	writeJSON(w, http.StatusOK, m)
}

func errJSON(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]any{"error": msg})
}

// params merges a JSON body or urlencoded form into a map for handler reads.
func params(r *http.Request) map[string]any {
	m := map[string]any{}
	if strings.Contains(strings.ToLower(r.Header.Get("Content-Type")), "application/json") {
		dec := json.NewDecoder(r.Body)
		dec.UseNumber()
		_ = dec.Decode(&m)
		return m
	}
	_ = r.ParseForm()
	for k, vs := range r.Form {
		if len(vs) > 0 {
			m[k] = vs[len(vs)-1]
		}
	}
	return m
}

func pstr(m map[string]any, key string) string {
	switch v := m[key].(type) {
	case string:
		return v
	case json.Number:
		return v.String()
	case nil:
		return ""
	default:
		return fmt.Sprint(v)
	}
}

func pint(m map[string]any, key string) int {
	switch v := m[key].(type) {
	case json.Number:
		n, err := v.Int64()
		if err != nil {
			return 0
		}
		return int(n)
	case float64:
		return int(v)
	case string:
		n := 0
		fmt.Sscanf(v, "%d", &n)
		return n
	}
	return 0
}

func pbool(m map[string]any, key string) bool {
	switch v := m[key].(type) {
	case bool:
		return v
	case string:
		return v == "true" || v == "1" || v == "on"
	}
	return false
}
