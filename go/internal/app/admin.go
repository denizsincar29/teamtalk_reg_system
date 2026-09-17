package app

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

func randToken() string {
	var b [32]byte
	if _, err := rand.Read(b[:]); err != nil {
		return fmt.Sprintf("%d", time.Now().UnixNano())
	}
	return hex.EncodeToString(b[:])
}

// Status modes: the UI and stored scheduler tasks use the Python logical codes
// (0=online, 1=away, 2=question); the wire needs TeamTalk statusmode bitflags
// (away=0x02, question=0x80). These two helpers translate in both directions.
func logicalToFlag(mode int) int {
	switch mode {
	case 1:
		return 0x02 // TT_STATUSMODE_AWAY
	case 2:
		return 0x80 // TT_STATUSMODE_QUESTION
	}
	return 0
}

func rawToLogical(raw int) int {
	switch {
	case raw&0x02 != 0:
		return 1
	case raw&0x80 != 0:
		return 2
	}
	return 0
}

// ---- login / logout ----

func (s *Server) login(w http.ResponseWriter, r *http.Request) {
	username := strings.TrimSpace(r.FormValue("username"))
	password := r.FormValue("password")
	next := safeNext(r.FormValue("next"))
	fail := func(msg string) {
		s.render(w, "login.html", viewData{"Error": msg, "Next": next})
	}
	if username == "" || password == "" {
		fail("Введи ник и пароль.")
		return
	}
	found, isAdmin, err := s.svc.AuthenticateAdmin(username, password)
	if err != nil {
		fail("Сервер TeamTalk сейчас недоступен. Попробуй позже.")
		return
	}
	if !found || !isAdmin {
		fail("Неверный ник или пароль (нужна учётка с правами администратора).")
		return
	}
	tok := s.newSession(username)
	http.SetCookie(w, &http.Cookie{
		Name: sessionCookie, Value: tok,
		Path: "/admin", HttpOnly: true, SameSite: http.SameSiteLaxMode,
		MaxAge: int(sessionTTL / time.Second),
	})
	if next == "" {
		next = "/admin/"
	}
	http.Redirect(w, r, next, http.StatusFound)
}

// safeNext keeps the deep link a notification tapped into alive across the
// login form: the guard sends /admin/?account=… to /admin/login?next=…, and the
// dashboard opens on that account once the password is in. Only paths inside
// /admin are let through, so the form cannot be turned into an open redirect.
func safeNext(next string) string {
	if !strings.HasPrefix(next, "/admin") || strings.Contains(next, "//") ||
		strings.Contains(next, "..") || strings.ContainsAny(next, "\r\n") {
		return ""
	}
	return next
}

func (s *Server) logout(w http.ResponseWriter, r *http.Request) {
	if c, err := r.Cookie(sessionCookie); err == nil {
		s.mu.Lock()
		delete(s.sessions, c.Value)
		s.mu.Unlock()
	}
	http.SetCookie(w, &http.Cookie{
		Name: sessionCookie, Value: "",
		Path: "/admin", HttpOnly: true, SameSite: http.SameSiteLaxMode,
		MaxAge: -1,
	})
	http.Redirect(w, r, "/admin/login", http.StatusFound)
}

// ---- pages ----

func (s *Server) pageDashboard(w http.ResponseWriter, r *http.Request) {
	s.render(w, "admin.html", viewData{})
}

// ---- read API ----

func (s *Server) overview(w http.ResponseWriter, r *http.Request) {
	statusMode, statusMsg := s.svc.GetStatus()
	cur, _ := s.svc.CurrentChannel()
	ch := s.svc.channelName(cur)
	if ch == "" && cur != 0 {
		ch = "/"
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"connected":      s.svc.Connected(),
		"nickname":       s.cfg.BotNickname,
		"channel_id":     cur,
		"channel_name":   ch,
		"status_mode":    rawToLogical(statusMode),
		"status_message": statusMsg,
	})
}

func (s *Server) apiStatus(w http.ResponseWriter, r *http.Request) {
	mode, msg := s.svc.GetStatus()
	writeJSON(w, http.StatusOK, map[string]any{
		"status_mode":    rawToLogical(mode),
		"status_message": msg,
	})
}

func (s *Server) apiAccounts(w http.ResponseWriter, r *http.Request) {
	accts, err := s.svc.Accounts()
	if err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"accounts": accts})
}

// accountByName resolves the account named in the path, or writes the error
// response and reports ok=false. Used by the per-account actions below.
func (s *Server) accountByName(w http.ResponseWriter, r *http.Request) (name, password string, ok bool) {
	name = strings.TrimSpace(r.PathValue("username"))
	if name == "" {
		errJSON(w, http.StatusBadRequest, "username required")
		return "", "", false
	}
	pw, found, err := s.svc.AccountPassword(name)
	if err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return "", "", false
	}
	if !found {
		errJSON(w, http.StatusNotFound, "account not found")
		return "", "", false
	}
	return name, pw, true
}

// apiAccountTTFile streams a ready-to-use .tt file for one account. The file is
// generated on the fly from the password the server itself reports, so nothing
// is stored and the file is never stale.
func (s *Server) apiAccountTTFile(w http.ResponseWriter, r *http.Request) {
	name, pw, ok := s.accountByName(w, r)
	if !ok {
		return
	}
	w.Header().Set("Content-Type", "application/xml")
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%q", name+".tt"))
	_, _ = w.Write([]byte(ttFileXML(s.cfg, name, pw)))
}

// apiAccountTTURL returns the tt:// URL for one account, for the copy button.
func (s *Server) apiAccountTTURL(w http.ResponseWriter, r *http.Request) {
	name, pw, ok := s.accountByName(w, r)
	if !ok {
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"username":  name,
		"url":       ttURL(s.cfg, name, pw),
		"short_url": ttShortURL(s.cfg, name, pw),
	})
}

// apiAccountBan bans the account name, so it holds even while the user is
// offline (an online-only ban would be gone after the next kick).
func (s *Server) apiAccountBan(w http.ResponseWriter, r *http.Request) {
	name := strings.TrimSpace(r.PathValue("username"))
	if name == "" {
		errJSON(w, http.StatusBadRequest, "username required")
		return
	}
	if err := s.svc.BanUsername(name); err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	okJSON(w, nil)
}

func (s *Server) apiAccountUnban(w http.ResponseWriter, r *http.Request) {
	name := strings.TrimSpace(r.PathValue("username"))
	if name == "" {
		errJSON(w, http.StatusBadRequest, "username required")
		return
	}
	if err := s.svc.UnbanUsername(name); err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	okJSON(w, nil)
}

// apiAccountDelete removes the account permanently.
func (s *Server) apiAccountDelete(w http.ResponseWriter, r *http.Request) {
	name := strings.TrimSpace(r.PathValue("username"))
	if name == "" {
		errJSON(w, http.StatusBadRequest, "username required")
		return
	}
	if err := s.svc.DeleteAccount(name); err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	okJSON(w, nil)
}

func (s *Server) apiUsers(w http.ResponseWriter, r *http.Request) {
	users, err := s.svc.Users()
	if err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"users": users})
}

func (s *Server) apiChannels(w http.ResponseWriter, r *http.Request) {
	chs, err := s.svc.Channels()
	if err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"channels": chs})
}

func (s *Server) apiMessages(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"messages": s.svc.Messages()})
}

func (s *Server) apiEvents(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"events": s.svc.Events()})
}

// apiMsgStream is the SSE live feed (parity with the Python admin stream):
// every second it pushes a data: frame holding the current messages and events.
func (s *Server) apiMsgStream(w http.ResponseWriter, r *http.Request) {
	fl, ok := w.(http.Flusher)
	if !ok {
		errJSON(w, http.StatusInternalServerError, "streaming unsupported")
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("X-Accel-Buffering", "no")

	send := func() {
		frame, _ := json.Marshal(map[string]any{
			"messages": s.svc.Messages(),
			"events":   s.svc.Events(),
		})
		fmt.Fprintf(w, "data: %s\n\n", frame)
		fl.Flush()
	}
	send()
	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-r.Context().Done():
			return
		case <-ticker.C:
			send()
		}
	}
}

// ---- action API ----

func (s *Server) apiBroadcast(w http.ResponseWriter, r *http.Request) {
	msg := strings.TrimSpace(pstr(params(r), "message"))
	if msg == "" {
		errJSON(w, http.StatusBadRequest, "empty message")
		return
	}
	if err := s.svc.SendBroadcast(msg); err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	okJSON(w, nil)
}

func (s *Server) apiSendMessage(w http.ResponseWriter, r *http.Request) {
	p := params(r)
	msg := strings.TrimSpace(pstr(p, "message"))
	if msg == "" {
		errJSON(w, http.StatusBadRequest, "empty message")
		return
	}
	uid := pint(p, "user_id")
	if uid == 0 {
		if uname := strings.TrimSpace(pstr(p, "username")); uname != "" {
			users, err := s.svc.Users()
			if err != nil {
				errJSON(w, http.StatusBadGateway, err.Error())
				return
			}
			for _, u := range users {
				if strings.EqualFold(u.Username, uname) {
					uid = u.ID
					break
				}
			}
		}
	}
	if uid == 0 {
		errJSON(w, http.StatusBadRequest, "no such online user")
		return
	}
	if err := s.svc.SendPrivateMessage(uid, msg); err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	okJSON(w, nil)
}

func (s *Server) apiSendChannelMessage(w http.ResponseWriter, r *http.Request) {
	msg := strings.TrimSpace(pstr(params(r), "message"))
	if msg == "" {
		errJSON(w, http.StatusBadRequest, "empty message")
		return
	}
	if err := s.svc.SendChannelMessage(msg); err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	okJSON(w, nil)
}

func (s *Server) apiChannelJoin(w http.ResponseWriter, r *http.Request) {
	id := pint(params(r), "channel_id")
	if id <= 0 {
		errJSON(w, http.StatusBadRequest, "channel_id required")
		return
	}
	if err := s.svc.JoinChannel(id); err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	okJSON(w, nil)
}

func (s *Server) apiChannelLeave(w http.ResponseWriter, r *http.Request) {
	if err := s.svc.LeaveChannel(); err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	okJSON(w, nil)
}

func (s *Server) apiMessagesClear(w http.ResponseWriter, r *http.Request) {
	s.svc.ClearMessages()
	okJSON(w, nil)
}

func (s *Server) apiEventsClear(w http.ResponseWriter, r *http.Request) {
	s.svc.ClearEvents()
	okJSON(w, nil)
}

func (s *Server) apiKick(w http.ResponseWriter, r *http.Request) {
	uid := pint(params(r), "user_id")
	if uid <= 0 {
		errJSON(w, http.StatusBadRequest, "user_id required")
		return
	}
	if err := s.svc.KickUser(uid); err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	okJSON(w, nil)
}

func (s *Server) apiBan(w http.ResponseWriter, r *http.Request) {
	uid := pint(params(r), "user_id")
	if uid <= 0 {
		errJSON(w, http.StatusBadRequest, "user_id required")
		return
	}
	if err := s.svc.BanUser(uid); err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	okJSON(w, nil)
}

func (s *Server) apiBanUsername(w http.ResponseWriter, r *http.Request) {
	name := strings.TrimSpace(pstr(params(r), "username"))
	if name == "" {
		errJSON(w, http.StatusBadRequest, "username required")
		return
	}
	if err := s.svc.BanUsername(name); err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	okJSON(w, nil)
}

func (s *Server) apiSetStatus(w http.ResponseWriter, r *http.Request) {
	p := params(r)
	mode := logicalToFlag(pint(p, "status_mode"))
	msg := pstr(p, "status_message")
	if err := s.svc.SetStatus(mode, msg); err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	okJSON(w, nil)
}

// ---- scheduler tasks API ----

func (s *Server) apiTasks(w http.ResponseWriter, r *http.Request) {
	tasks := s.sched.Tasks()
	if tasks == nil {
		tasks = []task{}
	}
	writeJSON(w, http.StatusOK, map[string]any{"tasks": tasks})
}

func (s *Server) apiTaskCreate(w http.ResponseWriter, r *http.Request) {
	p := params(r)
	typ := strings.TrimSpace(pstr(p, "type"))
	if typ == "" {
		errJSON(w, http.StatusBadRequest, "task type required")
		return
	}
	id, err := s.sched.AddTask(
		typ,
		strings.TrimSpace(pstr(p, "name")),
		pstr(p, "message"),
		pint(p, "channel_id"),
		strings.TrimSpace(pstr(p, "scheduled_time")),
		pint(p, "recurring_minutes"),
		strings.TrimSpace(pstr(p, "target_username")),
		pint(p, "delay_min_seconds"),
		pint(p, "delay_max_seconds"),
		pint(p, "status_mode"),
	)
	if err != nil {
		errJSON(w, http.StatusBadRequest, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, map[string]any{"id": id})
}

func (s *Server) apiTaskUpdate(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	p := params(r)
	if !s.sched.UpdateTask(id, p) {
		errJSON(w, http.StatusNotFound, "no such task")
		return
	}
	okJSON(w, nil)
}

func (s *Server) apiTaskDelete(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if !s.sched.DeleteTask(id) {
		errJSON(w, http.StatusNotFound, "no such task")
		return
	}
	okJSON(w, nil)
}

func (s *Server) apiTaskToggle(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if !s.sched.ToggleTask(id) {
		errJSON(w, http.StatusNotFound, "no such task")
		return
	}
	okJSON(w, nil)
}

func (s *Server) apiTaskRun(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if err := s.sched.RunNow(id); err != nil {
		errJSON(w, http.StatusBadGateway, err.Error())
		return
	}
	okJSON(w, nil)
}

// ---- offline PM queue API ----

func (s *Server) apiQueue(w http.ResponseWriter, r *http.Request) {
	q := s.sched.OfflinePMQueue()
	if q == nil {
		q = map[string][]offlinePM{}
	}
	writeJSON(w, http.StatusOK, map[string]any{"queue": q})
}

func (s *Server) apiQueueAdd(w http.ResponseWriter, r *http.Request) {
	p := params(r)
	username := strings.TrimSpace(pstr(p, "username"))
	msg := strings.TrimSpace(pstr(p, "message"))
	if username == "" || msg == "" {
		errJSON(w, http.StatusBadRequest, "username and message required")
		return
	}
	s.sched.QueueOfflinePM(username, msg, strings.TrimSpace(pstr(p, "task_name")))
	okJSON(w, nil)
}

func (s *Server) apiQueueClear(w http.ResponseWriter, r *http.Request) {
	username := r.PathValue("username")
	if !s.sched.ClearOfflinePM(username) {
		errJSON(w, http.StatusNotFound, "no queued PMs for that username")
		return
	}
	okJSON(w, nil)
}
