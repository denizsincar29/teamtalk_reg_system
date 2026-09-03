package app

import (
	"errors"
	"strings"
	"sync"
	"time"

	tt "github.com/denizsincar29/teamtalk_reg_system/go/teamtalk"
)

const (
	maxEvents = 100
	maxMsgs   = 100
)

const timeLayout = "2006-01-02 15:04:05"

// userRef remembers how a user displayed itself on the wire. Removal events
// ("loggedout", "removeuser") carry only a user id, so the last seen name is
// kept here instead of re-querying the pruned user map.
type userRef struct {
	user string
	nick string
}

// Service hosts the TeamTalk bot, buffers the events/messages it observes and
// executes every action the web/admin API needs. It reconnects automatically
// when the connection drops. All methods are safe for concurrent use.
type Service struct {
	cfg  Config
	done chan struct{}

	mu        sync.Mutex
	bot       *tt.Bot
	connected bool
	disconn   chan struct{}
	msgs      []msgRec
	evts      []evRec
	names     map[int]userRef
	chanNames map[int]string
	partial   map[string]string

	sched *Scheduler // wired after construction
}

func nowStr() string { return time.Now().Format(timeLayout) }

// NewService builds a Service. Call Start to begin connecting.
func NewService(cfg Config) *Service {
	return &Service{
		cfg:       cfg,
		done:      make(chan struct{}),
		disconn:   make(chan struct{}),
		names:     make(map[int]userRef),
		chanNames: make(map[int]string),
		partial:   make(map[string]string),
	}
}

// Connected reports whether the bot is currently logged in.
func (s *Service) Connected() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.connected
}

// Start launches the reconnect supervisor in the background.
func (s *Service) Start() {
	go s.supervise()
}

func (s *Service) Stop() {
	close(s.done)
	s.mu.Lock()
	b := s.bot
	s.mu.Unlock()
	if b != nil {
		b.Close()
	}
}

func (s *Service) supervise() {
	failedAt := time.Time{}
	firstFail := true
	for {
		select {
		case <-s.done:
			return
		default:
		}

		// Read connected + wait channel atomically: onDisconnect swaps the
		// channel under the same lock, so we either see "disconnected" now or
		// hold the very channel that the next disconnect closes to wake us.
		s.mu.Lock()
		connected := s.connected
		waitCh := s.disconn
		s.mu.Unlock()

		if connected {
			select {
			case <-s.done:
				return
			case <-waitCh:
				continue // reconnect below
			}
		}

		if err := s.tryConnect(); err != nil {
			if firstFail {
				firstFail = false
				s.pushEv(evRec{Type: "bot_connect_failed", Time: nowStr()})
				notify(s.cfg.NtfyURL, "Bot connection failed", "Could not connect to TeamTalk server", []string{"warning"}, 4)
				failedAt = time.Now()
			} else if time.Since(failedAt) > time.Minute {
				// Periodic reminder while the server stays down.
				failedAt = time.Now()
				notify(s.cfg.NtfyURL, "Bot connection failed", "Could not connect to TeamTalk server", []string{"warning"}, 4)
			}
		} else {
			firstFail = true
		}

		select {
		case <-s.done:
			return
		case <-time.After(3 * time.Second):
		}
	}
}

func (s *Service) tryConnect() error {
	cfg := s.cfg
	bot := tt.NewBot(tt.BotHandler{OnEvent: s.onEvent, OnDisconnect: s.onDisconnect})
	if err := bot.Connect(tt.BotConfig{
		Host:       cfg.BotHost,
		Port:       cfg.TCPPort,
		Nickname:   cfg.BotNickname,
		Username:   cfg.BotUsername,
		Password:   cfg.BotPassword,
		ClientName: "teamtalk-reg Go",
		Version:    "5.14.0",
	}); err != nil {
		return err
	}
	if cfg.BotJoinChannelID > 0 {
		_ = bot.JoinChannel(cfg.BotJoinChannelID, "")
	}

	s.mu.Lock()
	s.bot = bot
	s.connected = true
	s.disconn = make(chan struct{})
	s.pushEvLocked(evRec{Type: "bot_connected", Time: nowStr()})
	s.mu.Unlock()
	return nil
}

func (s *Service) onDisconnect(err error) {
	s.mu.Lock()
	s.connected = false
	s.pushEvLocked(evRec{Type: "connection_lost", Time: nowStr()})
	old := s.disconn
	s.disconn = make(chan struct{}) // fresh channel for the next connection
	s.mu.Unlock()
	if old != nil {
		close(old) // wake the supervisor so it reconnects
	}
	_ = err
}

// ----- helpers (callers hold no locks) -----

// bot returns the live bot or an error when not connected.
func (s *Service) botLive() (*tt.Bot, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if !s.connected || s.bot == nil {
		return nil, errors.New("Not connected")
	}
	return s.bot, nil
}

func (s *Service) pushEv(e evRec) {
	s.mu.Lock()
	s.pushEvLocked(e)
	s.mu.Unlock()
}

func (s *Service) pushEvLocked(e evRec) {
	s.evts = append(s.evts, e)
	if len(s.evts) > maxEvents {
		s.evts = s.evts[len(s.evts)-maxEvents:]
	}
}

func (s *Service) pushMsg(m msgRec) {
	s.mu.Lock()
	s.msgs = append(s.msgs, m)
	if len(s.msgs) > maxMsgs {
		s.msgs = s.msgs[len(s.msgs)-maxMsgs:]
	}
	s.mu.Unlock()
}

func (s *Service) rememberUser(uid int, user, nick string) {
	if uid == 0 {
		return
	}
	s.mu.Lock()
	s.names[uid] = userRef{user: user, nick: nick}
	s.mu.Unlock()
}

// resolveUser returns the best-known (username, nickname) for a user id.
func (s *Service) resolveUser(uid int) (string, string) {
	s.mu.Lock()
	ref, ok := s.names[uid]
	s.mu.Unlock()
	if ok {
		return ref.user, ref.nick
	}
	b, err := s.botLive()
	if err != nil {
		return "", ""
	}
	if u := b.User(uid); u != nil {
		s.rememberUser(uid, u.Username, u.Nickname)
		return u.Username, u.Nickname
	}
	return "", ""
}

// channelName resolves a channel id to a display name (best effort).
func (s *Service) channelName(id int) string {
	if id == 0 {
		return ""
	}
	s.mu.Lock()
	name, ok := s.chanNames[id]
	s.mu.Unlock()
	if ok {
		return name
	}
	b, err := s.botLive()
	if err != nil {
		return ""
	}
	var name2 string
	if c := b.Channel(id); c != nil {
		name2 = c.Name
	}
	if name2 == "" {
		if p := b.ChannelPath(id); p != "/" {
			name2 = p
		}
	}
	s.mu.Lock()
	s.chanNames[id] = name2
	s.mu.Unlock()
	return name2
}

func (s *Service) isSelf(uid int, username string) bool {
	b, err := s.botLive()
	myID := 0
	if err == nil {
		myID = b.MyID()
	}
	if uid != 0 && myID != 0 && uid == myID {
		return true
	}
	if username != "" && strings.EqualFold(username, s.cfg.BotUsername) {
		return true
	}
	return false
}

// ----- event handlers (called from the bot's read loop) -----

func (s *Service) onEvent(e tt.Event) {
	uid := e.UserID()
	switch e.Kind {
	case tt.EvMessage:
		s.onMessage(e)
	case tt.EvUserLoggedIn:
		s.rememberUser(uid, e.Line.Str(tt.KeyUsername), e.Line.Str(tt.KeyNickname))
		user, nick := s.resolveUser(uid)
		if s.isSelf(uid, e.Line.Str(tt.KeyUsername)) || uid == 0 {
			return
		}
		s.pushEv(evRec{Type: "user_login", Username: user, Nickname: nick, UserID: uid, Time: nowStr()})
		notify(s.cfg.NtfyURL, "User connected", nick+" ("+user+") joined the server", []string{"green_circle"}, 3)
		go s.onUserLogin(uid)
	case tt.EvUserLoggedOut:
		if uid == 0 {
			return
		}
		user, nick := s.resolveUser(uid)
		if s.isSelf(uid, user) {
			return
		}
		s.pushEv(evRec{Type: "user_logout", Username: user, Nickname: nick, Time: nowStr()})
	case tt.EvUserJoined:
		chanid := e.ChannelID()
		if uid == 0 {
			return // own channel join
		}
		s.rememberUser(uid, e.Line.Str(tt.KeyUsername), e.Line.Str(tt.KeyNickname))
		user, nick := s.resolveUser(uid)
		if s.isSelf(uid, user) {
			return
		}
		s.pushEv(evRec{Type: "user_join_channel", Username: user, Nickname: nick, Channel: s.channelName(chanid), Time: nowStr()})
	case tt.EvUserLeft:
		chanid := e.ChannelID()
		if uid == 0 {
			return
		}
		user, nick := s.resolveUser(uid)
		if s.isSelf(uid, user) {
			return
		}
		s.pushEv(evRec{Type: "user_left_channel", Username: user, Nickname: nick, Channel: s.channelName(chanid), Time: nowStr()})
	case tt.EvUserAdded, tt.EvUserUpdated:
		s.rememberUser(uid, e.Line.Str(tt.KeyUsername), e.Line.Str(tt.KeyNickname))
	case tt.EvChannelAdded, tt.EvChannelUpdated:
		if id := e.ChannelID(); id != 0 && e.Line.Str(tt.KeyChannelName) != "" {
			s.mu.Lock()
			s.chanNames[id] = e.Line.Str(tt.KeyChannelName)
			s.mu.Unlock()
		}
		if e.Kind == tt.EvChannelAdded {
			s.pushEv(evRec{Type: "channel_new", Channel: s.channelName(e.ChannelID()), Time: nowStr()})
		}
	case tt.EvChannelRemoved:
		id := e.ChannelID()
		name := s.channelName(id)
		s.mu.Lock()
		delete(s.chanNames, id)
		s.mu.Unlock()
		s.pushEv(evRec{Type: "channel_delete", Channel: name, Time: nowStr()})
	case tt.EvAccountAdded:
		username := e.Line.Str(tt.KeyUsername)
		if username != "" && !strings.EqualFold(username, s.cfg.BotUsername) {
			s.pushEv(evRec{Type: "user_account_new", Username: username, Time: nowStr()})
			notify(s.cfg.NtfyURL, "New account created", "Account '"+username+"' was created", []string{"tada"}, 3)
		}
	case tt.EvUserKicked:
		// A "kicked" push reaches the kicked user only, so this is us.
		s.pushEv(evRec{Type: "bot_kicked", Channel: "", Time: nowStr()})
		notify(s.cfg.NtfyURL, "Bot was kicked", "Bot was kicked from the server", []string{"boot"}, 4)
	}
}

func (s *Service) onMessage(e tt.Event) {
	mt := e.MessageType()
	var kind string
	switch mt {
	case tt.MsgUser:
		kind = "private"
	case tt.MsgChannel:
		kind = "channel"
	case tt.MsgBroadcast:
		kind = "broadcast"
	default:
		return // MsgCustom and unknown are dropped, matching the Python bot
	}

	src := e.Line.Int(tt.KeySrcUserID)
	user, nick := s.resolveUser(src)
	if s.isSelf(src, user) {
		return
	}
	s.rememberUser(src, user, nick)
	from := nick
	if from == "" {
		from = user
	}

	more := e.Line.Int(tt.KeyMore) != 0
	key := strings.Join([]string{fmtItoa(src), kind}, ":")
	var content string
	if more {
		s.mu.Lock()
		s.partial[key] += e.Content()
		s.mu.Unlock()
		return
	}
	s.mu.Lock()
	content = s.partial[key] + e.Content()
	delete(s.partial, key)
	s.mu.Unlock()

	rec := msgRec{Type: kind, FromUser: from, Time: nowStr(), Content: content}
	switch mt {
	case tt.MsgChannel:
		rec.Channel = s.channelName(e.ChannelID())
	case tt.MsgBroadcast:
		rec.Channel = ""
	}
	s.pushMsg(rec)

	if kind == "private" {
		notify(s.cfg.NtfyURL, "PM from "+from, content, []string{"speech_balloon"}, 4)
	}
}

func fmtItoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var b [20]byte
	i := len(b)
	for n > 0 {
		i--
		b[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		b[i] = '-'
	}
	return string(b[i:])
}

func (s *Service) onUserLogin(uid int) {
	user, _ := s.resolveUser(uid)
	if s.sched != nil {
		s.sched.OnUserLogin(user, uid)
	}
}

// ----- read access for the web layer -----

func (s *Service) Messages() []msgRec {
	s.mu.Lock()
	defer s.mu.Unlock()
	out := make([]msgRec, len(s.msgs))
	copy(out, s.msgs)
	return out
}

func (s *Service) Events() []evRec {
	s.mu.Lock()
	defer s.mu.Unlock()
	out := make([]evRec, len(s.evts))
	copy(out, s.evts)
	return out
}

func (s *Service) ClearMessages() {
	s.mu.Lock()
	s.msgs = nil
	s.mu.Unlock()
}

func (s *Service) ClearEvents() {
	s.mu.Lock()
	s.evts = nil
	s.mu.Unlock()
}

// ----- account & user management -----

func (s *Service) Accounts() ([]acctView, error) {
	b, err := s.botLive()
	if err != nil {
		return nil, err
	}
	accts, err := b.ListAccounts()
	if err != nil {
		return nil, err
	}
	out := make([]acctView, 0, len(accts))
	for _, a := range accts {
		v := acctView{Username: a.Username, Note: a.Note}
		if a.UserType == tt.UserTypeAdmin {
			v.UserType = "admin"
		} else {
			v.UserType = "default"
		}
		out = append(out, v)
	}
	return out, nil
}

// AuthenticateAdmin checks a username+password against the TeamTalk accounts:
// the caller is an admin only when the account exists, is usertype admin and
// the supplied password equals the stored one. found distinguishes "account
// missing" from "not an admin / wrong password".
func (s *Service) AuthenticateAdmin(username, password string) (found, isAdmin bool, err error) {
	b, err := s.botLive()
	if err != nil {
		return false, false, err
	}
	accts, err := b.ListAccounts()
	if err != nil {
		return false, false, err
	}
	want := strings.ToLower(username)
	for _, a := range accts {
		if strings.ToLower(a.Username) == want {
			return true, a.UserType == tt.UserTypeAdmin && a.Password == password, nil
		}
	}
	return false, false, nil
}

func (s *Service) CheckUserExists(username string) (bool, error) {
	b, err := s.botLive()
	if err != nil {
		return false, err
	}
	return b.AccountExists(username)
}

func (s *Service) CreateUser(username, password string) error {
	b, err := s.botLive()
	if err != nil {
		return err
	}
	if err := b.CreateAccount(username, password, tt.UserTypeDefault, 0, ""); err != nil {
		return err
	}
	// Announce the new registration on the server; never fail the signup if
	// the broadcast is rejected.
	if b.MyChannelID() != 0 {
		_ = b.SendBroadcast("New user registered: " + username)
	}
	notify(s.cfg.NtfyURL, "New user registered", "Username: "+username, []string{"tada"}, 3)
	return nil
}

// ----- actions -----

func (s *Service) Users() ([]userView, error) {
	b, err := s.botLive()
	if err != nil {
		return nil, err
	}
	users := b.Users()
	out := make([]userView, 0, len(users))
	for _, u := range users {
		out = append(out, userView{
			ID:       u.ID,
			Username: u.Username,
			Nickname: u.Nickname,
			Channel:  s.channelName(u.ChannelID),
			Status:   u.StatusMessage,
		})
	}
	return out, nil
}

func (s *Service) Channels() ([]chanView, error) {
	b, err := s.botLive()
	if err != nil {
		return nil, err
	}
	chs := b.Channels()
	out := make([]chanView, 0, len(chs))
	for _, c := range chs {
		name := c.Name
		path := b.ChannelPath(c.ID)
		if path == "/" && name == "" {
			name = "/"
		}
		out = append(out, chanView{
			ID: c.ID, Name: name, Path: path, ParentID: c.ParentID, MaxUsers: c.MaxUsers,
		})
	}
	return out, nil
}

func (s *Service) SendPrivateMessage(userID int, text string) error {
	b, err := s.botLive()
	if err != nil {
		return err
	}
	if b.User(userID) == nil {
		return errors.New("User not found")
	}
	return b.SendToUser(userID, text)
}

func (s *Service) SendChannelMessage(text string) error {
	b, err := s.botLive()
	if err != nil {
		return err
	}
	cur := b.MyChannelID()
	if cur == 0 {
		return errors.New("Bot is not in a channel")
	}
	return b.SendToChannel(cur, text)
}

func (s *Service) SendBroadcast(text string) error {
	b, err := s.botLive()
	if err != nil {
		return err
	}
	return b.SendBroadcast(text)
}

func (s *Service) JoinChannel(id int) error {
	b, err := s.botLive()
	if err != nil {
		return err
	}
	return b.JoinChannel(id, "")
}

func (s *Service) LeaveChannel() error {
	b, err := s.botLive()
	if err != nil {
		return err
	}
	return b.LeaveChannel()
}

func (s *Service) CurrentChannel() (int, error) {
	b, err := s.botLive()
	if err != nil {
		return 0, err
	}
	return b.MyChannelID(), nil
}

func (s *Service) KickUser(userID int) error {
	b, err := s.botLive()
	if err != nil {
		return err
	}
	return b.KickFromServer(userID)
}

func (s *Service) BanUser(userID int) error {
	b, err := s.botLive()
	if err != nil {
		return err
	}
	return b.BanUser(userID)
}

func (s *Service) BanUsername(username string) error {
	b, err := s.botLive()
	if err != nil {
		return err
	}
	return b.BanUsername(username)
}

func (s *Service) SetStatus(mode int, message string) error {
	b, err := s.botLive()
	if err != nil {
		return err
	}
	return b.ChangeStatus(mode, message)
}

func (s *Service) GetStatus() (int, string) {
	b, err := s.botLive()
	if err != nil {
		return 0, ""
	}
	u := b.User(b.MyID())
	if u == nil {
		return 0, ""
	}
	return u.StatusMode & 0xFF, u.StatusMessage
}
