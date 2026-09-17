package app

import "testing"

// The tap target of a push notification: an explicit ADMIN_TT_URL wins, and
// without one the address falls back to the bot account the deployment already
// carries. Percent-encoding matters — a password with @ or a space would
// otherwise split the URL in the wrong place.
func TestLoadAdminTTURL(t *testing.T) {
	t.Setenv("TEAMTALK_HOST", "example.org")
	t.Setenv("TEAMTALK_USERNAME", "bot")
	t.Setenv("TEAMTALK_PASSWORD", "p@ss word")
	t.Setenv("ADMIN_TT_URL", "")

	if got, want := Load().AdminTTURL, "tt://bot:p%40ss%20word@example.org:10333:10333/"; got != want {
		t.Errorf("fallback AdminTTURL = %q, want %q", got, want)
	}

	const explicit = "tt://denizsincar29:secret@example.org:10333:10333/"
	t.Setenv("ADMIN_TT_URL", explicit)
	if got := Load().AdminTTURL; got != explicit {
		t.Errorf("AdminTTURL = %q, want the configured %q", got, explicit)
	}

	// No credentials at all: no invented link, the notification just has no tap
	// target.
	t.Setenv("ADMIN_TT_URL", "")
	t.Setenv("TEAMTALK_PASSWORD", "")
	if got := Load().AdminTTURL; got != "" {
		t.Errorf("AdminTTURL = %q, want empty without credentials", got)
	}
}
