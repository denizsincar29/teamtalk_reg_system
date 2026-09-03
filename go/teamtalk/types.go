package teamtalk

import "time"

// Channel is a channel in the tree the server pushes after login.
type Channel struct {
	ID       int
	ParentID int
	Name     string
	Topic    string
	Type     int // Chan* bitmask
	MaxUsers int
}

// fromLine fills the channel from an addchannel/updatechannel push line.
func (c *Channel) fromLine(l Line) {
	c.ID = l.Int(KeyChannelID)
	c.ParentID = l.Int(KeyParentID)
	c.Name = l.Str(KeyChannelName)
	c.Topic = l.Str(KeyTopic)
	c.Type = l.Int(KeyChannelType)
	c.MaxUsers = l.Int(KeyMaxUsers)
}

// User is a connected user tracked from push events. Presence in a channel is
// best-effort: the wire only reports a user's channel on joined/left and on
// adduser pushes that carry chanid.
type User struct {
	ID            int
	Username      string
	Nickname      string
	StatusMode    int
	StatusMessage string
	IPAddr        string
	ChannelID     int
	UserType      int
}

// fromLine fills the user from an adduser/loggedin/updateuser push line.
func (u *User) fromLine(l Line) {
	u.ID = l.Int(KeyUserID)
	u.Username = l.Str(KeyUsername)
	u.Nickname = l.Str(KeyNickname)
	u.StatusMode = l.Int(KeyStatusMode)
	u.StatusMessage = l.Str(KeyStatusMessage)
	u.IPAddr = l.Str(KeyIPAddr)
	u.UserType = l.Int(KeyUserType)
	u.ChannelID = l.Int(KeyChannelID) // only adduser pushes carry chanid; others yield 0
}

// UserAccount is a user account as returned by the listaccounts reply rows.
// An admin listing accounts receives the stored password too (the server sends
// it for the whole account management workflow); it is used to authenticate
// web admins and must never be exposed to clients.
type UserAccount struct {
	Username    string
	Password    string
	UserType    int // UserTypeDefault / UserTypeAdmin
	UserRights  int
	Note        string
	InitChannel string
	LastLogin   string // textual timestamp, when the server sends one
}

// fromLine fills the account from a "useraccount" payload row.
func (a *UserAccount) fromLine(l Line) {
	a.Username = l.Str(KeyUsername)
	a.Password = l.Str(KeyPassword)
	a.UserType = l.Int(KeyUserType)
	a.UserRights = l.Int(KeyUserRights)
	a.Note = l.Str(KeyNoteField)
	a.InitChannel = l.Str(KeyInitChannel)
	a.LastLogin = l.Str(KeyLastLogin)
}

// EventKind classifies a server-pushed (id-less) line.
type EventKind int

const (
	EvUnknown EventKind = iota
	EvServerUpdate
	EvChannelAdded
	EvChannelUpdated
	EvChannelRemoved
	EvUserJoined     // a user joined a channel (may be us)
	EvUserLeft       // a user left a channel
	EvUserLoggedIn   // a user logged on to the server
	EvUserLoggedOut  // a user logged off
	EvUserAdded      // a full user record became visible (e.g. on channel join)
	EvUserUpdated    // a user changed status / nickname / etc.
	EvUserRemoved    // a user record disappeared from view
	EvUserKicked     // someone was kicked (fields say who/from where)
	EvUserBanned     // a ban notice
	EvMessage        // an incoming text message (PM, channel, or broadcast)
	EvAccountAdded   // a new user account was created (admin event)
	EvAccountRemoved // a user account was deleted (admin event)
	EvPong
)

// Event is one server-pushed line, delivered to the Bot's event handler.
type Event struct {
	Kind EventKind
	Line Line
	At   time.Time
}

// UserID is the user the event concerns (when the wire carries userid).
func (e Event) UserID() int { return e.Line.Int(KeyUserID) }

// ChannelID is the channel the event concerns (when the wire carries chanid).
func (e Event) ChannelID() int { return e.Line.Int(KeyChannelID) }

// MessageType returns the incoming message type for EvMessage.
func (e Event) MessageType() int { return e.Line.Int(KeyMsgType) }

// Content is the message text / server reason on events that carry it.
func (e Event) Content() string { return e.Line.Str(KeyContent) }

// classifyEvent maps a server push command name to an EventKind.
func classifyEvent(cmd string) EventKind {
	switch cmd {
	case SrvServerUpdate:
		return EvServerUpdate
	case SrvAddChannel:
		return EvChannelAdded
	case SrvUpdateChannel:
		return EvChannelUpdated
	case SrvRemoveChannel:
		return EvChannelRemoved
	case SrvJoined:
		return EvUserJoined
	case SrvLeftChannel:
		return EvUserLeft
	case SrvLoggedIn:
		return EvUserLoggedIn
	case SrvLoggedOut:
		return EvUserLoggedOut
	case SrvAddUser:
		return EvUserAdded
	case SrvUpdateUser:
		return EvUserUpdated
	case SrvRemoveUser:
		return EvUserRemoved
	case SrvKicked:
		return EvUserKicked
	case SrvBanned:
		return EvUserBanned
	case SrvMessageDeliver:
		return EvMessage
	case SrvAddUserAccount:
		return EvAccountAdded
	case SrvRemoveUserAccount:
		return EvAccountRemoved
	case SrvKeepAlive:
		return EvPong
	default:
		return EvUnknown
	}
}

// isPush reports whether a command name is a server push (id-less event) rather
// than a reply-payload row (like "useraccount" from listaccounts).
func isPush(cmd string) bool {
	switch cmd {
	case SrvServerUpdate, SrvAddChannel, SrvUpdateChannel, SrvRemoveChannel,
		SrvJoined, SrvLeftChannel, SrvLoggedIn, SrvLoggedOut, SrvAddUser,
		SrvUpdateUser, SrvRemoveUser, SrvKicked, SrvBanned, SrvMessageDeliver,
		SrvAddUserAccount, SrvRemoveUserAccount, SrvKeepAlive:
		return true
	default:
		return false
	}
}
