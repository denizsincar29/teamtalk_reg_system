package app

// The record shapes below mirror the dicts the Python system stored in its
// channel_messages / events buffers and returned from its API, so a client of
// the old API keeps working against the Go server unchanged.

// msgRec is one stored incoming message (channel / private / broadcast).
type msgRec struct {
	Type     string `json:"type"`
	FromUser string `json:"from_user"`
	Channel  string `json:"channel"`
	Content  string `json:"content"`
	Time     string `json:"time"`
}

// evRec is one stored server activity event.
type evRec struct {
	Type     string `json:"type"`
	Username string `json:"username,omitempty"`
	Nickname string `json:"nickname,omitempty"`
	UserID   int    `json:"user_id,omitempty"`
	Channel  string `json:"channel,omitempty"`
	Time     string `json:"time"`
}

// acctView is a user account as returned by the admin accounts API. It carries
// the password because the TeamTalk server hands it to an admin outright in the
// account listing, and the panel needs it to build .tt files and tt:// links.
type acctView struct {
	Username string `json:"username"`
	Password string `json:"password"`
	UserType string `json:"user_type"` // "admin" or "default"
	Note     string `json:"note"`
}

// userView is an online user as returned by the admin users API.
type userView struct {
	ID       int    `json:"id"`
	Username string `json:"username"`
	Nickname string `json:"nickname"`
	Channel  string `json:"channel"`
	Status   string `json:"status"`
}

// chanView is a channel as returned by the admin channels API.
type chanView struct {
	ID          int    `json:"id"`
	Name        string `json:"name"`
	Path        string `json:"path"`
	HasPassword bool   `json:"has_password"`
	ParentID    int    `json:"parent_id"`
	MaxUsers    int    `json:"max_users"`
}
