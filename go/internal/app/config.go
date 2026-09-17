package app

import (
	"os"
	"strconv"
)

// Config holds all server settings. Every value is read from the environment
// using the same variable names as the original Python application, so the
// systemd unit / .env used today keeps working unchanged.
type Config struct {
	// Public host advertised to end users in .tt files and tt:// URLs.
	PublicHost string
	// BotHost is what the bot dials (localhost when running next to the server).
	BotHost string
	// ShortHost is where the /tturl redirector answers. Messenger clients only
	// link https URLs, so an account shared in a chat travels as
	// https://<ShortHost>/tturl?... and lands on the tt:// address.
	ShortHost string
	TCPPort int
	UDPPort int

	// Bot credentials.
	BotUsername string
	BotPassword string
	BotNickname string
	// BotJoinChannelID > 0 makes the bot join that channel right after login.
	BotJoinChannelID int

	// Web listener.
	ListenAddr string

	// AdminTTURL is what a tap on a push notification opens — a ready tt://
	// address with credentials, so the owner lands in the client with one tap.
	// Set ADMIN_TT_URL to use a personal account; otherwise the address is
	// built from the bot credentials (which are admin on the server).
	AdminTTURL string

	// ntfy push notifications. Empty NtfyURL disables notifications.
	NtfyURL string

	// Scheduler data files live under DataDir (default "./data").
	DataDir string
}

func envStr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func envInt(key string, def int) int {
	if v := os.Getenv(key); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}

func envBool(key string, def bool) bool {
	v := os.Getenv(key)
	if v == "" {
		return def
	}
	b, err := strconv.ParseBool(v)
	if err != nil {
		return v == "1" || v == "yes"
	}
	return b
}

// Load reads the configuration from environment variables.
func Load() Config {
	host := envStr("TEAMTALK_HOST", "localhost")
	tcpPort := envInt("TEAMTALK_TCP_PORT", 10333)
	udpPort := envInt("TEAMTALK_UDP_PORT", 10333)

	username := envStr("TEAMTALK_USERNAME", "bot")

	// The bot dials localhost when the web app runs on the TeamTalk server
	// host, while end users keep connecting to the public host.
	botHost := host
	if envBool("USE_LOCALHOST_FOR_BOT", false) {
		botHost = "localhost"
	}

	ntfyServer := envStr("NTFY_SERVER", "")
	ntfyTopic := envStr("NTFY_TOPIC", "")
	ntfyURL := envStr("NTFY_URL", "")
	if ntfyURL == "" && ntfyServer != "" && ntfyTopic != "" {
		ntfyURL = ntfyServer + "/" + ntfyTopic
	}

	cfg := Config{
		PublicHost:       host,
		BotHost:          botHost,
		ShortHost:        envStr("TT_SHORT_HOST", "tt."+host),
		TCPPort:          tcpPort,
		UDPPort:          udpPort,
		BotUsername:      username,
		BotPassword:      os.Getenv("TEAMTALK_PASSWORD"),
		BotNickname:      envStr("TEAMTALK_NICKNAME", username),
		BotJoinChannelID: envInt("BOT_JOIN_CHANNEL_ID", 0),
		ListenAddr:       envStr("APP_HOST", "0.0.0.0") + ":" + strconv.Itoa(envInt("APP_PORT", 8000)),
		NtfyURL:          ntfyURL,
		AdminTTURL:       envStr("ADMIN_TT_URL", ""),
		DataDir:          envStr("DATA_DIR", "data"),
	}
	// Without an explicit address the tap target is the bot account, whose
	// credentials the deployment already carries.
	if cfg.AdminTTURL == "" && cfg.BotUsername != "" && cfg.BotPassword != "" {
		cfg.AdminTTURL = ttURL(cfg, cfg.BotUsername, cfg.BotPassword)
	}
	return cfg
}
