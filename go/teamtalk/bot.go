package teamtalk

import (
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"
)

// Errors returned by Bot operations.
var (
	ErrClosed = errors.New("teamtalk: connection is closed")
)

// ServerError is a non-zero command error answered by the server
// ("error number=... message=...").
type ServerError struct {
	Num int
	Msg string
}

func (e *ServerError) Error() string {
	return fmt.Sprintf("server error %d: %s", e.Num, e.Msg)
}

// Reply is the collected answer envelope of one command.
//
// OK is true unless the server answered with an explicit "error" line: the
// TeamTalk text protocol does not send an "ok" terminator for every command,
// so the absence of an error (bounded by the matching "end") means success.
type Reply struct {
	OK     bool
	ErrNum int
	ErrMsg string
	// Rows holds the command's payload rows (e.g. "useraccount" rows from
	// listaccounts). Pushed event lines are never mixed in.
	Rows []Line
}

// BotConfig carries the parameters for Bot.Connect.
type BotConfig struct {
	Host       string
	Port       int
	Nickname   string
	Username   string // bot account username (must be admin for admin ops)
	Password   string
	ClientName string
	Version    string

	// NoAutoSubscribe disables auto-subscribing to messages from every user
	// that becomes visible. Subscription is what makes PMs and channel
	// messages arrive, so keep it enabled unless you handle subscribing
	// yourself. Default false (subscribe).
	NoAutoSubscribe bool
	// KeepAlive sends "ping" at this interval while connected; 0 disables.
	// Default 20s.
	KeepAlive time.Duration
}

// BotHandler receives bot lifecycle events. All methods are optional.
type BotHandler struct {
	// OnEvent fires for every server push event (state is already updated).
	OnEvent func(Event)
	// OnDisconnect fires when the read loop dies (network error, server close).
	// The bot is unusable afterwards; reconnect by building a new Bot.
	OnDisconnect func(err error)
}

// Bot is an event-driven text-protocol TeamTalk client. It keeps the channel,
// user and account state it has seen, and executes at most one command at a
// time so replies always match their request.
type Bot struct {
	c *Client

	cfg BotConfig
	hd  BotHandler

	// cmdMu serializes outstanding commands: only one request envelope may be
	// open at a time.
	cmdMu sync.Mutex
	// reqMu guards pending.
	reqMu   sync.Mutex
	pending *request

	stateMu  sync.Mutex
	channels map[int]*Channel
	users    map[int]*User
	accounts map[string]*UserAccount
	selfID   int
	selfChan int
	selfName string

	done        chan struct{}
	closeOnce   sync.Once
	intentional bool
}

type request struct {
	id     int
	ch     chan *Reply
	ok     bool
	errnum int
	errmsg string
	rows   []Line
}

// NewBot creates a Bot with a handler (may be empty).
func NewBot(hd BotHandler) *Bot {
	return &Bot{
		hd:       hd,
		channels: make(map[int]*Channel),
		users:    make(map[int]*User),
		accounts: make(map[string]*UserAccount),
		done:     make(chan struct{}),
	}
}

// Connect dials the server and logs the bot account in. Event delivery starts
// immediately after login.
func (b *Bot) Connect(cfg BotConfig) error {
	if cfg.Port == 0 {
		cfg.Port = 10333
	}
	if cfg.Version == "" {
		cfg.Version = "5.14.0"
	}
	if cfg.ClientName == "" {
		cfg.ClientName = "teamtalk-go bot"
	}

	c, err := Dial(cfg.Host, cfg.Port)
	if err != nil {
		return err
	}
	c.ReadTimeout = 45 * time.Second
	b.c = c
	b.cfg = cfg
	b.selfName = cfg.Username

	go b.readLoop()

	rep, err := b.Do(func(id int) string {
		return Login(cfg.Nickname, cfg.Username, cfg.Password, cfg.ClientName, cfg.Version, id)
	})
	if err != nil {
		b.Close()
		return err
	}
	for _, l := range rep.Rows {
		if l.Cmd == SrvLoginAccepted {
			if cfg.KeepAlive == 0 {
				cfg.KeepAlive = 20 * time.Second
			}
			if cfg.KeepAlive > 0 {
				go b.keepAlive(cfg.KeepAlive)
			}
			return nil
		}
	}
	b.Close()
	if !rep.OK || rep.ErrNum != 0 || rep.ErrMsg != "" {
		return &ServerError{Num: rep.ErrNum, Msg: rep.ErrMsg}
	}
	return errors.New("teamtalk: login rejected by server")
}

// Close logs out and closes the connection. Safe to call multiple times.
func (b *Bot) Close() error {
	if b.c == nil {
		return nil
	}
	b.intentional = true
	if err := b.c.Close(); err != nil {
		return err
	}
	b.failRead(ErrClosed)
	return nil
}

// MyID returns our own user id (0 until the server reports us among its users).
func (b *Bot) MyID() int { b.stateMu.Lock(); defer b.stateMu.Unlock(); return b.selfID }

// MyChannelID returns the id of the channel the bot is currently in.
func (b *Bot) MyChannelID() int { b.stateMu.Lock(); defer b.stateMu.Unlock(); return b.selfChan }

// Channels returns a snapshot of the known channels.
func (b *Bot) Channels() []*Channel {
	b.stateMu.Lock()
	defer b.stateMu.Unlock()
	out := make([]*Channel, 0, len(b.channels))
	for _, c := range b.channels {
		cp := *c
		out = append(out, &cp)
	}
	return out
}

// Channel returns one channel by id (nil when unknown).
func (b *Bot) Channel(id int) *Channel {
	b.stateMu.Lock()
	defer b.stateMu.Unlock()
	if c, ok := b.channels[id]; ok {
		cp := *c
		return &cp
	}
	return nil
}

// Users returns a snapshot of the known users.
func (b *Bot) Users() []*User {
	b.stateMu.Lock()
	defer b.stateMu.Unlock()
	out := make([]*User, 0, len(b.users))
	for _, u := range b.users {
		up := *u
		out = append(out, &up)
	}
	return out
}

// User returns one user by id (nil when unknown).
func (b *Bot) User(id int) *User {
	b.stateMu.Lock()
	defer b.stateMu.Unlock()
	if u, ok := b.users[id]; ok {
		up := *u
		return &up
	}
	return nil
}

// ChannelPath resolves the "/"-joined path of a channel from the tree. The
// unnamed root channel contributes nothing, so a top-level channel has the
// path "/Name" and the root itself "/".
func (b *Bot) ChannelPath(id int) string {
	b.stateMu.Lock()
	defer b.stateMu.Unlock()
	var names []string
	seen := map[int]bool{}
	for id != 0 && id != -1 {
		if seen[id] {
			break
		}
		seen[id] = true
		c, ok := b.channels[id]
		if !ok {
			break
		}
		if c.Name != "" {
			names = append([]string{c.Name}, names...)
		}
		id = c.ParentID
	}
	if len(names) == 0 {
		return "/"
	}
	return "/" + strings.Join(names, "/")
}

// ----- request plumbing -----

// Do executes a command, waiting for its reply envelope. build receives the
// allocated command id and must produce the full wire line for it.
func (b *Bot) Do(build func(cmdid int) string) (*Reply, error) {
	b.cmdMu.Lock()
	defer b.cmdMu.Unlock()

	b.reqMu.Lock()
	if b.pending != nil {
		b.reqMu.Unlock()
		return nil, errors.New("teamtalk: internal: request already pending")
	}
	id := b.c.NextCmdID()
	req := &request{id: id, ch: make(chan *Reply, 1), ok: true}
	b.pending = req
	line := build(id)
	err := b.c.Send(line)
	if err != nil {
		b.pending = nil
		b.reqMu.Unlock()
		return nil, err
	}
	b.reqMu.Unlock()

	select {
	case rep := <-req.ch:
		return rep, nil
	case <-b.done:
		return nil, ErrClosed
	}
}

// readLoop is the single reader goroutine. It routes envelope lines
// (begin/ok/error/end) to the pending request, dispatches pushes to the
// handler, and collects reply payload rows into the open request.
func (b *Bot) readLoop() {
	for {
		l, err := b.c.ReadLine()
		if err != nil {
			b.failRead(err)
			return
		}
		switch l.Cmd {
		case SrvBeginCmd:
			// envelope start; the boundary we care about is "end"
		case SrvCommandOK, SrvError:
			b.applyEnvelope(l)
		case SrvEndCmd:
			if b.complete(l) {
				continue
			}
		default:
			if isPush(l.Cmd) {
				b.dispatch(l)
				continue
			}
			// not a push: a payload row for the open request, if any
			if b.collectRow(l) {
				continue
			}
			b.dispatch(l) // stray unknown line: surface it anyway
		}
	}
}

// applyEnvelope records ok/error fields on the pending request whose id matches.
func (b *Bot) applyEnvelope(l Line) {
	b.reqMu.Lock()
	defer b.reqMu.Unlock()
	p := b.pending
	if p == nil || p.id != l.Int(KeyCmdID) {
		return
	}
	if l.Cmd == SrvError {
		p.ok = false
		p.errnum = l.Int(KeyErrorNum)
		p.errmsg = l.Str(KeyErrorMessage)
	}
}

// collectRow appends a payload row to the pending request (id-less rows belong
// to the open envelope). Reports whether a request was open.
func (b *Bot) collectRow(l Line) bool {
	b.reqMu.Lock()
	defer b.reqMu.Unlock()
	if p := b.pending; p != nil {
		p.rows = append(p.rows, l)
		return true
	}
	return false
}

// complete resolves the pending request whose id matches the "end" line.
// Returns true when a request was completed.
func (b *Bot) complete(l Line) bool {
	b.reqMu.Lock()
	p := b.pending
	if p == nil || p.id != l.Int(KeyCmdID) {
		b.reqMu.Unlock()
		return false
	}
	b.pending = nil
	b.reqMu.Unlock()
	p.ch <- &Reply{OK: p.ok, ErrNum: p.errnum, ErrMsg: p.errmsg, Rows: p.rows}
	return true
}

// dispatch updates internal state for a push and forwards it to the handler.
func (b *Bot) dispatch(l Line) {
	b.applyState(l)
	if b.hd.OnEvent != nil {
		b.hd.OnEvent(Event{Kind: classifyEvent(l.Cmd), Line: l, At: time.Now()})
	}
}

func (b *Bot) failRead(err error) {
	b.closeOnce.Do(func() {
		b.reqMu.Lock()
		b.pending = nil
		b.reqMu.Unlock()
		close(b.done)
	})
	if !b.intentional && b.hd.OnDisconnect != nil {
		b.hd.OnDisconnect(err)
	}
}

func (b *Bot) keepAlive(interval time.Duration) {
	t := time.NewTicker(interval)
	defer t.Stop()
	for {
		select {
		case <-b.done:
			return
		case <-t.C:
			_ = b.c.Send(Ping())
		}
	}
}

// applyState keeps the channel/user/account maps in sync with pushes.
func (b *Bot) applyState(l Line) {
	b.stateMu.Lock()
	defer b.stateMu.Unlock()

	switch classifyEvent(l.Cmd) {
	case EvChannelAdded, EvChannelUpdated:
		id := l.Int(KeyChannelID)
		if id == 0 {
			return
		}
		c, ok := b.channels[id]
		if !ok {
			c = &Channel{}
			b.channels[id] = c
		}
		c.fromLine(l)
	case EvChannelRemoved:
		delete(b.channels, l.Int(KeyChannelID))
	case EvUserJoined:
		chanid := l.Int(KeyChannelID)
		uid := l.Int(KeyUserID)
		if uid == 0 {
			// "joined" without a userid is the server telling us (the bot)
			// that we entered chanid ourselves.
			b.selfChan = chanid
			return
		}
		u := b.users[uid]
		if u == nil {
			u = &User{ID: uid}
			b.users[uid] = u
		}
		u.fromLine(l)
		u.ChannelID = chanid
		if u.Username == b.selfName && b.selfName != "" {
			b.selfID = uid
			b.selfChan = chanid
		}
	case EvUserLeft:
		if u := b.users[l.Int(KeyUserID)]; u != nil {
			u.fromLine(l)
			u.ChannelID = 0
		}
	case EvUserLoggedIn, EvUserAdded, EvUserUpdated:
		uid := l.Int(KeyUserID)
		if uid == 0 {
			return
		}
		u, ok := b.users[uid]
		if !ok {
			u = &User{}
			b.users[uid] = u
		}
		u.fromLine(l)
		if u.Username == b.selfName && b.selfName != "" {
			b.selfID = uid
			// adduser about ourselves carries our current channel.
			if u.ChannelID != 0 {
				b.selfChan = u.ChannelID
			}
		}
	case EvUserLoggedOut, EvUserRemoved:
		if u := b.users[l.Int(KeyUserID)]; u != nil {
			if u.ID == b.selfID {
				b.selfID = 0
			}
			delete(b.users, u.ID)
		}
	case EvAccountAdded:
		name := l.Str(KeyUsername)
		if name != "" {
			a := b.accounts[name]
			if a == nil {
				a = &UserAccount{}
				b.accounts[name] = a
			}
			a.fromLine(l)
		}
	case EvAccountRemoved:
		delete(b.accounts, l.Str(KeyUsername))
	}

	if !b.cfg.NoAutoSubscribe {
		switch classifyEvent(l.Cmd) {
		case EvUserLoggedIn, EvUserAdded:
			if uid := l.Int(KeyUserID); uid != 0 && l.Str(KeyUsername) != b.selfName {
				go b.subscribeUser(uid)
			}
		}
	}
}

// subscribeUser asks the server to deliver this user's messages to us.
func (b *Bot) subscribeUser(userID int) {
	sub := SubUserMsg | SubChannelMsg | SubBroadcastMsg | SubCustomMsg
	rep, err := b.Do(func(id int) string { return Subscribe(userID, sub, id) })
	if err != nil || rep == nil {
		return
	}
	_ = rep
}
