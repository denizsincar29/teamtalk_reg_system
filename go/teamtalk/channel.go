package teamtalk

// ChannelConfig describes a channel for the makechannel/updatechannel/join-new
// commands (mirrors Common.h ChannelProp). Zero values are omitted from the
// wire line and the server fills its own defaults; audio codec properties are
// deliberately not transmitted (TeamTalk v5 servers reject/ignore them and a
// text-only bot never streams).
type ChannelConfig struct {
	ID         int    // existing channel id (updatechannel)
	ParentID   int    // parent under which a new channel is created
	Name       string // channel name
	Password   string
	OpPassword string
	Topic      string
	Type       int // Chan* bitmask (ChanDefault, ChanPermanent, ...)
	MaxUsers   int
	DiskQuota  int // per-user file quota in bytes
	UserData   string

	// Per-stream transmit lists; empty means all channel members may transmit.
	VoiceUsers      []int
	VideoUsers      []int
	DesktopUsers    []int
	MediaFileUsers  []int
	ChannelMsgUsers []int

	SoloDelay      int // seconds a solo-transmit user keeps the mic (v5.10)
	TotalVoice     int // max simultaneous voice transmitters
	TotalMediaFile int // max simultaneous media-file transmitters
}

// emitStr and emitInt append a property only when the value is meaningful, so
// generated lines stay close to the C++ client's without empty noise.
func emitStr(pairs *[]any, key, val string) {
	if val != "" {
		*pairs = append(*pairs, key, val)
	}
}

func emitInt(pairs *[]any, key string, val int) {
	if val != 0 {
		*pairs = append(*pairs, key, val)
	}
}

func emitList(pairs *[]any, key string, val []int) {
	if len(val) > 0 {
		*pairs = append(*pairs, key, val)
	}
}

// emitStreamProps appends the transmit-user lists and channel totals shared by
// all channel commands, in the order used by ClientNode.cpp.
func emitStreamProps(pairs *[]any, c ChannelConfig) {
	emitList(pairs, KeyVoiceUsers, c.VoiceUsers)
	emitList(pairs, KeyVideoUsers, c.VideoUsers)
	emitList(pairs, KeyDesktopUsers, c.DesktopUsers)
	emitList(pairs, KeyMediaFileUsers, c.MediaFileUsers)
	emitList(pairs, KeyChanMsgUsers, c.ChannelMsgUsers)
	if c.SoloDelay != 0 {
		emitInt(pairs, KeyTransmitSwitch, c.SoloDelay)
	}
	emitInt(pairs, KeyTotalVoice, c.TotalVoice)
	emitInt(pairs, KeyTotalMediaFile, c.TotalMediaFile)
}

// JoinNewChannel builds a "join" command that creates and immediately joins a
// new channel under ParentID (mirrors DoJoinChannel for an unknown channel).
func JoinNewChannel(c ChannelConfig, cmdid int) string {
	pairs := []any{}
	emitStr(&pairs, KeyChannelName, c.Name)
	emitInt(&pairs, KeyParentID, c.ParentID)
	emitStr(&pairs, KeyTopic, c.Topic)
	emitStr(&pairs, KeyOpPassword, c.OpPassword)
	emitInt(&pairs, KeyChannelType, c.Type)
	emitStr(&pairs, KeyUserData, c.UserData)
	emitStreamProps(&pairs, c)
	pairs = append(pairs, KeyPassword, c.Password, KeyCmdID, cmdid)
	return Build(CmdJoinChannel, pairs)
}

// MakeChannel builds the "makechannel" command (mirrors DoMakeChannel).
func MakeChannel(c ChannelConfig, cmdid int) string {
	pairs := []any{}
	emitInt(&pairs, KeyParentID, c.ParentID)
	emitStr(&pairs, KeyChannelName, c.Name)
	emitStr(&pairs, KeyPassword, c.Password)
	emitStr(&pairs, KeyTopic, c.Topic)
	emitInt(&pairs, KeyDiskQuota, c.DiskQuota)
	emitStr(&pairs, KeyOpPassword, c.OpPassword)
	emitInt(&pairs, KeyMaxUsers, c.MaxUsers)
	emitInt(&pairs, KeyChannelType, c.Type)
	emitStr(&pairs, KeyUserData, c.UserData)
	emitStreamProps(&pairs, c)
	pairs = append(pairs, KeyCmdID, cmdid)
	return Build(CmdMakeChannel, pairs)
}

// UpdateChannel builds the "updatechannel" command (mirrors DoUpdateChannel).
func UpdateChannel(c ChannelConfig, cmdid int) string {
	pairs := []any{KeyChannelID, c.ID}
	emitStr(&pairs, KeyChannelName, c.Name)
	emitStr(&pairs, KeyPassword, c.Password)
	emitStr(&pairs, KeyTopic, c.Topic)
	emitInt(&pairs, KeyDiskQuota, c.DiskQuota)
	emitStr(&pairs, KeyOpPassword, c.OpPassword)
	emitInt(&pairs, KeyMaxUsers, c.MaxUsers)
	emitInt(&pairs, KeyChannelType, c.Type)
	emitStr(&pairs, KeyUserData, c.UserData)
	emitStreamProps(&pairs, c)
	pairs = append(pairs, KeyCmdID, cmdid)
	return Build(CmdUpdateChannel, pairs)
}

// RemoveChannel builds the "removechannel" command.
func RemoveChannel(channelID int, cmdid int) string {
	return Build(CmdRemoveChannel, []any{KeyChannelID, channelID, KeyCmdID, cmdid})
}
