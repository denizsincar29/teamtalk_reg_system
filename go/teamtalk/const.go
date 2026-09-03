// Package teamtalk implements the text-based TeamTalk 5 client protocol.
//
// The command channel is plain TCP text lines (see Library/TeamTalkLib in
// github.com/BearWare/TeamTalk5): a command name followed by
// key="escaped value" / key=number / key=[list] properties, terminated by \r\n.
// This package needs no TeamTalk SDK: only the raw text protocol, which is all
// a chat/administration bot requires (no audio/video streaming).
package teamtalk

// ProtocolVersion is the TeamTalk protocol version sent in "login"
// (TEAMTALK_PROTOCOL_VERSION in Commands.h).
const ProtocolVersion = "5.14"

// EOL terminates every command and response line.
const EOL = "\r\n"

// Client command tokens (client -> server), from Commands.h CLIENT_*.
const (
	CmdLogin         = "login"
	CmdLogout        = "logout"
	CmdChangeNick    = "changenick"
	CmdChangeStatus  = "changestatus"
	CmdJoinChannel   = "join"
	CmdLeaveChannel  = "leave"
	CmdMessage       = "message"
	CmdKeepAlive     = "ping"
	CmdKick          = "kick"
	CmdMakeChannel   = "makechannel"
	CmdUpdateChannel = "updatechannel"
	CmdRemoveChannel = "removechannel"
	CmdMoveUser      = "moveuser"
	CmdChannelOp     = "op"
	CmdBan           = "ban"
	CmdUnban         = "unban"
	CmdListBans      = "listbans"
	CmdListAccounts  = "listaccounts"
	CmdNewAccount    = "newaccount"
	CmdDelAccount    = "delaccount"
	CmdSubscribe     = "subscribe"
	CmdUnsubscribe   = "unsubscribe"
	CmdQuit          = "quit"
)

// Server command tokens (server -> client), from Commands.h SERVER_*.
const (
	SrvWelcome           = "teamtalk"
	SrvLoginAccepted     = "accepted"
	SrvServerUpdate      = "serverupdate"
	SrvError             = "error"
	SrvKeepAlive         = "pong"
	SrvAddChannel        = "addchannel"
	SrvUpdateChannel     = "updatechannel"
	SrvRemoveChannel     = "removechannel"
	SrvJoined            = "joined"
	SrvLeftChannel       = "left"
	SrvLoggedIn          = "loggedin"
	SrvLoggedOut         = "loggedout"
	SrvAddUser           = "adduser"
	SrvUpdateUser        = "updateuser"
	SrvRemoveUser        = "removeuser"
	SrvUserAccount       = "useraccount"
	SrvAddUserAccount    = "adduseraccount"
	SrvRemoveUserAccount = "removeuseraccount"
	SrvMessageDeliver    = "messagedeliver"
	SrvKicked            = "kicked"
	SrvBanned            = "userbanned"
	SrvBeginCmd          = "begin"
	SrvEndCmd            = "end"
	SrvCommandOK         = "ok"
)

// Property keys, from Commands.h TT_* string macros.
const (
	KeyUserID             = "userid"
	KeyNickname           = "nickname"
	KeyContent            = "content"
	KeyUsername           = "username"
	KeyPassword           = "password"
	KeyStatusMode         = "statusmode"
	KeyStatusMessage      = "statusmsg"
	KeyIPAddr             = "ipaddr"
	KeyTCPPort            = "tcpport"
	KeyUDPPort            = "udpport"
	KeyVersion            = "version"
	KeyServerName         = "servername"
	KeyUserRights         = "userrights"
	KeyChannelID          = "chanid"
	KeyParentID           = "parentid"
	KeyChannelName        = "name"
	KeyTopic              = "topic"
	KeyOpPassword         = "oppassword"
	KeyChannel            = "channel"
	KeyInitChannel        = "initchan"
	KeyProtocol           = "protocol"
	KeyPacketProtocol     = "packetprotocol"
	KeyClientName         = "clientname"
	KeyMsgType            = "type"
	KeySrcUserID          = "srcuserid"
	KeyDestUserID         = "destuserid"
	KeyErrorNum           = "number"
	KeyErrorMessage       = "message"
	KeyCmdID              = "id"
	KeyUserType           = "usertype"
	KeyNoteField          = "note"
	KeyAutoOpChannels     = "opchannels"
	KeyAudioBPSLimit      = "audiocodeclimit"
	KeyCmdFlood           = "cmdflood"
	KeyBanTime            = "bantime"
	KeyMOTD               = "motd"
	KeySubscribers        = "subscribers"
	KeyAudioCodec         = "audiocodec"
	KeyAudioConfig        = "audiocfg"
	KeyMaxUsers           = "maxusers"
	KeyDiskQuota          = "diskquota"
	KeyChanMsgUsers       = "chanmsgusers"
	KeyVoiceUsers         = "voiceusers"
	KeyVideoUsers         = "videousers"
	KeyDesktopUsers       = "desktopusers"
	KeyMediaFileUsers     = "mediafileusers"
	KeyOperatorStatus     = "opstatus"
	KeyLocalSubscriptions = "sublocal"
	KeyIndex              = "index"
	KeyCount              = "count"
	KeyLastLogin          = "lastlogin"
	KeyTotalVoice         = "voicetot"
	KeyTotalMediaFile     = "mediafiletot"
	KeyTransmitSwitch     = "switchdelay"
	KeyUserData           = "userdata"
	KeyMore               = "more"
	KeyChannelType        = "type" // channel type uses the same "type" key
	KeyBanType            = "type" // ban type uses the same "type" key
)

// Message types (MsgType), Common.h. "message"/"messagedeliver" carry type=.
const (
	MsgNone      = 0
	MsgUser      = 1 // TTUserMsg: private message to a user
	MsgChannel   = 2 // TTChannelMsg: message to a channel
	MsgBroadcast = 3 // TTBroadcastMsg: message to every channel
	MsgCustom    = 4 // TTCustomMsg: app-defined message to a user
)

// User types (UserType), Common.h. newaccount sends usertype=.
const (
	UserTypeDefault = 0x01 // USERTYPE_DEFAULT
	UserTypeAdmin   = 0x02 // USERTYPE_ADMIN
)

// Channel types (ChannelType), Common.h.
const (
	ChanDefault           = 0x0000
	ChanPermanent         = 0x0001
	ChanSoloTransmit      = 0x0002
	ChanClassroom         = 0x0004
	ChanOperatorRecvOnly  = 0x0008
	ChanNoVoiceActivation = 0x0010
	ChanNoRecording       = 0x0020
	ChanHidden            = 0x0040
)

// Ban types (BanType), Common.h. ban/unban carry type=.
const (
	BanNone     = 0x00
	BanChannel  = 0x01
	BanIPAddr   = 0x02
	BanUsername = 0x04
	BanDefault  = BanIPAddr
)

// Subscriptions, Common.h. subscribe/unsubscribe carry sublocal=.
const (
	SubNone         = 0x00000000
	SubUserMsg      = 0x00000001
	SubChannelMsg   = 0x00000002
	SubBroadcastMsg = 0x00000004
	SubCustomMsg    = 0x00000008
	SubVoice        = 0x00000010
	SubVideoCapture = 0x00000020
	SubDesktop      = 0x00000040
	SubDesktopInput = 0x00000080
	SubMediaFile    = 0x00000100
	SubAll          = 0x000001FF
	SubLocalDefault = SubUserMsg | SubChannelMsg | SubBroadcastMsg | SubCustomMsg | SubMediaFile
)

// User rights (UserRight), Common.h, as used when creating accounts.
const (
	RightMultiLogin        = 0x00000001
	RightViewAllUsers      = 0x00000002
	RightCreateTempChannel = 0x00000004
	RightModifyChannels    = 0x00000008
	RightTextMsgBroadcast  = 0x00000010
	RightKickUsers         = 0x00000020
	RightBanUsers          = 0x00000040
	RightMoveUsers         = 0x00000080
	RightUploadFiles       = 0x00000200
	RightDownloadFiles     = 0x00000400
	RightUpdateServerProps = 0x00000800
	RightTransmitVoice     = 0x00001000
	RightTransmitVideo     = 0x00002000
	RightTransmitDesktop   = 0x00004000
	RightTransmitMediaFile = 0x00030000
	RightLockedNickname    = 0x00040000
	RightLockedStatus      = 0x00080000
	RightTextMsgUser       = 0x00400000
	RightTextMsgChannel    = 0x00800000
)

// DefaultUserRights mirrors DEFAULT_USER_RIGHTS used by the original
// registration bot for newly registered accounts.
const DefaultUserRights = RightMultiLogin | RightViewAllUsers |
	RightCreateTempChannel | RightUploadFiles | RightDownloadFiles |
	RightTransmitVoice | RightTransmitVideo | RightTransmitDesktop |
	RightTransmitMediaFile | RightTextMsgUser | RightTextMsgChannel

// Status modes used by the registration bot's status logic (0/1/2),
// matching the original Python application.
const (
	StatusOnline   = 0
	StatusAway     = 1
	StatusQuestion = 2
)
