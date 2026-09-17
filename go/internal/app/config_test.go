package app

import "testing"

// The tap target of a push notification. ADMIN_TT_URL names the account (a
// personal admin one, or the bot when unset), and the click that actually
// travels is the https /tturl redirector — a phone will not open a tt://
// address straight from a notification.
func TestLoadClickURL(t *testing.T) {
	t.Setenv("TEAMTALK_HOST", "example.org")
	t.Setenv("TEAMTALK_USERNAME", "bot")
	t.Setenv("TEAMTALK_PASSWORD", "p@ss word")
	t.Setenv("ADMIN_TT_URL", "")

	cfg := Load()
	if got, want := cfg.AdminTTURL, "tt://example.org?tcpport=10333&udpport=10333&encrypted=false&username=bot&password=p%40ss%20word"; got != want {
		t.Errorf("fallback AdminTTURL = %q, want %q", got, want)
	}
	// base64url of "p@ss word", unpadded, is what the link carries.
	if got, want := cfg.ClickURL, "https://tt.example.org/open?u=bot&p=cEBzcyB3b3Jk"; got != want {
		t.Errorf("fallback ClickURL = %q, want %q", got, want)
	}

	// The persona account from .env: the credentials are cut out of the tt://
	// address and re-encoded into the landing-page link.
	t.Setenv("ADMIN_TT_URL", "tt://denizsincar29:secret@example.org:10333:10333/")
	cfg = Load()
	if got, want := cfg.ClickURL, "https://tt.example.org/open?u=denizsincar29&p=c2VjcmV0"; got != want {
		t.Errorf("ClickURL = %q, want %q", got, want)
	}

	// An https address is already a click target: used verbatim.
	const explicit = "https://tt.example.org/tturl?u=x&p=y"
	t.Setenv("ADMIN_TT_URL", explicit)
	if got := Load().ClickURL; got != explicit {
		t.Errorf("ClickURL = %q, want the configured %q", got, explicit)
	}

	// Nothing to log in with: no invented link, the notification simply has no
	// tap target.
	t.Setenv("ADMIN_TT_URL", "")
	t.Setenv("TEAMTALK_PASSWORD", "")
	if got := Load().ClickURL; got != "" {
		t.Errorf("ClickURL = %q, want empty without credentials", got)
	}
}
