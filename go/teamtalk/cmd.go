package teamtalk

import (
	"fmt"
	"strconv"
	"strings"
)

// escape prepares a string value for embedding in a command line, mirroring
// PrepareString in Commands.cpp: backslash, double-quote, CR and LF are escaped.
func escape(s string) string {
	var b strings.Builder
	b.Grow(len(s) + 8)
	for i := 0; i < len(s); i++ {
		switch c := s[i]; c {
		case '\\':
			b.WriteString(`\\`)
		case '"':
			b.WriteString(`\"`)
		case '\r':
			b.WriteString(`\r`)
		case '\n':
			b.WriteString(`\n`)
		default:
			b.WriteByte(c)
		}
	}
	return b.String()
}

func strVal(key, value string) string { return " " + key + "=\"" + escape(value) + "\"" }
func intVal(key string, v int) string { return " " + key + "=" + strconv.Itoa(v) }

func listVal(key string, v []int) string {
	if len(v) == 0 {
		return ""
	}
	parts := make([]string, len(v))
	for i, x := range v {
		parts[i] = strconv.Itoa(x)
	}
	return " " + key + "=[" + strings.Join(parts, ",") + "]"
}

// Build assembles a client command line: cmd + ordered pairs + EOL. Pairs are
// key/value alternates; values must be string, int or []int.
func Build(cmd string, pairs []any) string {
	var b strings.Builder
	b.WriteString(cmd)
	for i := 0; i+1 < len(pairs); i += 2 {
		key, ok := pairs[i].(string)
		if !ok {
			continue
		}
		switch v := pairs[i+1].(type) {
		case string:
			b.WriteString(strVal(key, v))
		case int:
			b.WriteString(intVal(key, v))
		case []int:
			b.WriteString(listVal(key, v))
		default:
			b.WriteString(strVal(key, fmt.Sprint(v)))
		}
	}
	b.WriteString(EOL)
	return b.String()
}

// Login builds the "login" client command (mirrors ClientNode::DoLogin).
func Login(nickname, username, password, clientname, version string, cmdid int) string {
	return Build(CmdLogin, []any{
		KeyNickname, nickname,
		KeyUsername, username,
		KeyPassword, password,
		KeyClientName, clientname,
		KeyProtocol, ProtocolVersion,
		KeyVersion, version,
		KeyCmdID, cmdid,
	})
}

// Logout builds the "logout" client command.
func Logout(cmdid int) string {
	return Build(CmdLogout, []any{KeyCmdID, cmdid})
}

// ChangeNickname builds the "changenick" client command.
func ChangeNickname(nickname string, cmdid int) string {
	return Build(CmdChangeNick, []any{KeyNickname, nickname, KeyCmdID, cmdid})
}

// ChangeStatus builds the "changestatus" client command.
func ChangeStatus(mode int, statusmsg string, cmdid int) string {
	return Build(CmdChangeStatus, []any{KeyStatusMode, mode, KeyStatusMessage, statusmsg, KeyCmdID, cmdid})
}

// Ping builds a keepalive "ping" without a command id; the server answers
// "pong" which the reader drops. Mirrors DoPing(issue_cmdid=false).
func Ping() string { return CmdKeepAlive + EOL }

// Message builds a text-message client command (mirrors ClientNode::DoTextMessage).
// msgType: MsgUser / MsgChannel / MsgBroadcast / MsgCustom.
// more marks a truncated continuation so the server reassembles the chunks.
func Message(msgType, toUserID, toChannelID int, content string, more bool, cmdid int) string {
	pairs := []any{KeyMsgType, msgType, KeyContent, content}
	switch msgType {
	case MsgUser, MsgCustom:
		pairs = append(pairs, KeyDestUserID, toUserID)
	case MsgChannel:
		pairs = append(pairs, KeyChannelID, toChannelID)
	}
	if more {
		pairs = append(pairs, KeyMore, 1)
	} else {
		pairs = append(pairs, KeyMore, 0)
	}
	pairs = append(pairs, KeyCmdID, cmdid)
	return Build(CmdMessage, pairs)
}

// LeaveChannel builds the "leave" client command (leave the channel we are in).
func LeaveChannel(cmdid int) string {
	return Build(CmdLeaveChannel, []any{KeyCmdID, cmdid})
}

// JoinChannel builds "join" for an already-existing channel.
func JoinChannel(channelID int, password string, cmdid int) string {
	return Build(CmdJoinChannel, []any{KeyChannelID, channelID, KeyPassword, password, KeyCmdID, cmdid})
}

// KickUser builds the "kick" client command. channelID 0 kicks from the whole
// server (needs a user with server-wide kick rights).
func KickUser(userID, channelID int, cmdid int) string {
	pairs := []any{}
	if channelID != 0 {
		pairs = append(pairs, KeyChannelID, channelID)
	}
	pairs = append(pairs, KeyUserID, userID, KeyCmdID, cmdid)
	return Build(CmdKick, pairs)
}

// ChannelOp builds the "op" client command: op=true makes userID an operator
// of channelID, op=false removes the operator flag. opPassword is only needed
// when we are not already an operator.
func ChannelOp(userID, channelID int, op bool, opPassword string, cmdid int) string {
	pairs := []any{
		KeyChannelID, channelID,
		KeyUserID, userID,
		KeyOperatorStatus, boolToInt(op),
	}
	if opPassword != "" {
		pairs = append(pairs, KeyOpPassword, opPassword)
	}
	pairs = append(pairs, KeyCmdID, cmdid)
	return Build(CmdChannelOp, pairs)
}

// MoveUser builds the "moveuser" client command.
func MoveUser(userID, toChannelID int, cmdid int) string {
	return Build(CmdMoveUser, []any{KeyUserID, userID, KeyChannelID, toChannelID, KeyCmdID, cmdid})
}

func boolToInt(b bool) int {
	if b {
		return 1
	}
	return 0
}

// BannedUser describes a ban for the ban/unban commands (Common.h BannedUser).
type BannedUser struct {
	BanType  int // BanChannel / BanIPAddr / BanUsername (Common.h)
	IPAddr   string
	Username string
	ChanPath string // full "Parent/Child" channel path, used for BanChannel
	Nickname string
}

// BanUser builds the "ban" client command (mirrors ClientNode::DoBanUser).
// userID > 0 bans the currently logged-in user; otherwise identify by IP,
// username or channel path.
func BanUser(userID int, ban BannedUser, cmdid int) string {
	pairs := []any{}
	if userID > 0 {
		pairs = append(pairs, KeyUserID, userID)
	}
	if ban.IPAddr != "" {
		pairs = append(pairs, KeyIPAddr, ban.IPAddr)
	}
	pairs = append(pairs, KeyBanType, ban.BanType)
	if ban.Username != "" {
		pairs = append(pairs, KeyUsername, ban.Username)
	}
	if ban.ChanPath != "" {
		pairs = append(pairs, KeyChannel, ban.ChanPath)
	}
	if ban.Nickname != "" {
		pairs = append(pairs, KeyNickname, ban.Nickname)
	}
	pairs = append(pairs, KeyCmdID, cmdid)
	return Build(CmdBan, pairs)
}

// UnBanUser builds the "unban" client command.
func UnBanUser(ban BannedUser, cmdid int) string {
	return Build(CmdUnban, []any{
		KeyIPAddr, ban.IPAddr,
		KeyBanType, ban.BanType,
		KeyUsername, ban.Username,
		KeyChannel, ban.ChanPath,
		KeyCmdID, cmdid,
	})
}

// ListBans builds the "listbans" client command. index/count page the result;
// channelID > 0 limits to bans on that channel.
func ListBans(index, count, channelID int, cmdid int) string {
	pairs := []any{KeyIndex, index, KeyCount, count}
	if channelID > 0 {
		pairs = append(pairs, KeyChannelID, channelID)
	}
	pairs = append(pairs, KeyCmdID, cmdid)
	return Build(CmdListBans, pairs)
}

// ListAccounts builds the "listaccounts" client command.
func ListAccounts(index, count int, cmdid int) string {
	return Build(CmdListAccounts, []any{KeyIndex, index, KeyCount, count, KeyCmdID, cmdid})
}

// Account describes a user account for the newaccount command
// (Common.h UserAccount). Only the non-zero fields are transmitted.
type Account struct {
	Username       string
	Password       string
	UserType       int // UserTypeDefault / UserTypeAdmin
	UserRights     int // bitmask of Right*; 0 asks the server for its default
	UserData       string
	Note           string
	InitChannel    string
	AutoOpChannels []int
	AudioBPSLimit  int // user's allowed audio bitrate; wire key "audiocodeclimit"
}

// NewAccount builds the "newaccount" client command (mirrors DoNewUserAccount).
func NewAccount(acct Account, cmdid int) string {
	pairs := []any{
		KeyUsername, acct.Username,
		KeyPassword, acct.Password,
		KeyUserType, acct.UserType,
	}
	if acct.UserRights != 0 {
		pairs = append(pairs, KeyUserRights, acct.UserRights)
	}
	if acct.UserData != "" {
		pairs = append(pairs, KeyUserData, acct.UserData)
	}
	if acct.Note != "" {
		pairs = append(pairs, KeyNoteField, acct.Note)
	}
	if acct.InitChannel != "" {
		pairs = append(pairs, KeyInitChannel, acct.InitChannel)
	}
	if len(acct.AutoOpChannels) > 0 {
		pairs = append(pairs, KeyAutoOpChannels, acct.AutoOpChannels)
	}
	if acct.AudioBPSLimit != 0 {
		pairs = append(pairs, KeyAudioBPSLimit, acct.AudioBPSLimit)
	}
	pairs = append(pairs, KeyCmdID, cmdid)
	return Build(CmdNewAccount, pairs)
}

// DelAccount builds the "delaccount" client command.
func DelAccount(username string, cmdid int) string {
	return Build(CmdDelAccount, []any{KeyUsername, username, KeyCmdID, cmdid})
}

// Subscribe builds the "subscribe" client command (mirrors DoSubscribe).
// userID 0 targets every user currently in the channel we are in.
func Subscribe(userID, subscriptions int, cmdid int) string {
	return Build(CmdSubscribe, []any{KeyUserID, userID, KeyLocalSubscriptions, subscriptions, KeyCmdID, cmdid})
}

// Unsubscribe builds the "unsubscribe" client command.
func Unsubscribe(userID, subscriptions int, cmdid int) string {
	return Build(CmdUnsubscribe, []any{KeyUserID, userID, KeyLocalSubscriptions, subscriptions, KeyCmdID, cmdid})
}
