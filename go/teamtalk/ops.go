package teamtalk

import (
	"strings"
	"unicode/utf8"
)

// maxMsgLen is the safe content length for one text-message chunk; longer text
// is split and reassembled by the server via the "more" continuation flag.
const maxMsgLen = 900

// exec runs a command and returns a server-error when the server answered with
// an "error" envelope line.
func (b *Bot) exec(build func(int) string) (*Reply, error) {
	rep, err := b.Do(build)
	if err != nil {
		return nil, err
	}
	if !rep.OK {
		return rep, &ServerError{Num: rep.ErrNum, Msg: rep.ErrMsg}
	}
	return rep, nil
}

// AccountExists reports whether an account with this username exists
// (case-insensitive), mirroring the Python registration bot's check_user.
func (b *Bot) AccountExists(username string) (bool, error) {
	rep, err := b.exec(func(id int) string { return ListAccounts(0, 10000, id) })
	if err != nil {
		return false, err
	}
	want := strings.ToLower(username)
	for _, l := range rep.Rows {
		if l.Cmd == SrvUserAccount && strings.ToLower(l.Str(KeyUsername)) == want {
			return true, nil
		}
	}
	return false, nil
}

// ListAccounts returns all user accounts known to the server.
func (b *Bot) ListAccounts() ([]*UserAccount, error) {
	rep, err := b.exec(func(id int) string { return ListAccounts(0, 10000, id) })
	if err != nil {
		return nil, err
	}
	out := make([]*UserAccount, 0, len(rep.Rows))
	for _, l := range rep.Rows {
		if l.Cmd == SrvUserAccount {
			a := &UserAccount{}
			a.fromLine(l)
			out = append(out, a)
		}
	}
	return out, nil
}

// CreateAccount registers a new user account. userType is UserTypeDefault or
// UserTypeAdmin; zero userrights applies DefaultUserRights.
func (b *Bot) CreateAccount(username, password string, userType, userRights int, note string) error {
	if userType == 0 {
		userType = UserTypeDefault
	}
	if userRights == 0 {
		userRights = DefaultUserRights
	}
	_, err := b.exec(func(id int) string {
		return NewAccount(Account{
			Username: username, Password: password,
			UserType: userType, UserRights: userRights,
			Note: note,
		}, id)
	})
	return err
}

// DeleteAccount removes a user account.
func (b *Bot) DeleteAccount(username string) error {
	_, err := b.exec(func(id int) string { return DelAccount(username, id) })
	return err
}

// ChangeStatus updates the bot's status. mode: StatusOnline/Away/Question.
func (b *Bot) ChangeStatus(mode int, message string) error {
	_, err := b.exec(func(id int) string { return ChangeStatus(mode, message, id) })
	return err
}

// ChangeNickname updates the bot's nickname.
func (b *Bot) ChangeNickname(nickname string) error {
	_, err := b.exec(func(id int) string { return ChangeNickname(nickname, id) })
	return err
}

// SendToUser sends a private text message to one user.
func (b *Bot) SendToUser(userID int, text string) error {
	return b.sendMessage(MsgUser, userID, 0, text)
}

// SendToChannel sends a text message to a channel.
func (b *Bot) SendToChannel(channelID int, text string) error {
	return b.sendMessage(MsgChannel, 0, channelID, text)
}

// SendBroadcast sends a text message to every channel on the server
// (needs the RightTextMsgBroadcast user right).
func (b *Bot) SendBroadcast(text string) error {
	return b.sendMessage(MsgBroadcast, 0, 0, text)
}

func (b *Bot) sendMessage(msgType, toUser, toChan int, text string) error {
	chunks := chunkText(text, maxMsgLen)
	for i, chunk := range chunks {
		more := i < len(chunks)-1
		rep, err := b.exec(func(id int) string { return Message(msgType, toUser, toChan, chunk, more, id) })
		if err != nil {
			return err
		}
		_ = rep
	}
	return nil
}

func chunkText(s string, maxRunes int) []string {
	if utf8.RuneCountInString(s) <= maxRunes {
		return []string{s}
	}
	var chunks []string
	for len(s) > 0 {
		if utf8.RuneCountInString(s) <= maxRunes {
			chunks = append(chunks, s)
			break
		}
		// cut at rune boundary
		n := 0
		for i := range s {
			if n == maxRunes {
				chunks = append(chunks, s[:i])
				s = s[i:]
				break
			}
			n++
		}
	}
	return chunks
}

// KickFromServer kicks a user off the whole server (admin right required).
func (b *Bot) KickFromServer(userID int) error {
	_, err := b.exec(func(id int) string { return KickUser(userID, 0, id) })
	return err
}

// KickFromChannel kicks a user out of a specific channel (operator right).
func (b *Bot) KickFromChannel(userID, channelID int) error {
	_, err := b.exec(func(id int) string { return KickUser(userID, channelID, id) })
	return err
}

// BanUser bans an online user by their user id (IP ban).
func (b *Bot) BanUser(userID int) error {
	_, err := b.exec(func(id int) string {
		return BanUser(userID, BannedUser{BanType: BanIPAddr}, id)
	})
	return err
}

// BanUsername bans an account name even when the user is offline.
func (b *Bot) BanUsername(username string) error {
	_, err := b.exec(func(id int) string {
		return BanUser(0, BannedUser{BanType: BanUsername, Username: username}, id)
	})
	return err
}

// Unban removes a ban that matches the given fields.
func (b *Bot) Unban(ban BannedUser) error {
	_, err := b.exec(func(id int) string { return UnBanUser(ban, id) })
	return err
}

// ListBans lists the server's bans (chanid 0 lists server-wide bans).
func (b *Bot) ListBans(channelID int) ([]Line, error) {
	rep, err := b.exec(func(id int) string { return ListBans(0, 10000, channelID, id) })
	if err != nil {
		return nil, err
	}
	return rep.Rows, nil
}

// JoinChannel enters an existing channel by id, using its password when set.
func (b *Bot) JoinChannel(channelID int, password string) error {
	_, err := b.exec(func(id int) string { return JoinChannel(channelID, password, id) })
	return err
}

// LeaveChannel moves to the parent channel when the current channel has one,
// otherwise leaves to the vacuum (mirrors the Python bot's leave behavior).
func (b *Bot) LeaveChannel() error {
	b.stateMu.Lock()
	cur := b.selfChan
	parent := 0
	if c, ok := b.channels[cur]; ok {
		parent = c.ParentID
	}
	b.stateMu.Unlock()

	if parent > 0 {
		return b.JoinChannel(parent, "")
	}
	_, err := b.exec(func(id int) string { return LeaveChannel(id) })
	return err
}

// SubscribeToUser asks the server to deliver one user's messages to us.
func (b *Bot) SubscribeToUser(userID int) error {
	_, err := b.exec(func(id int) string { return Subscribe(userID, SubLocalDefault, id) })
	return err
}
