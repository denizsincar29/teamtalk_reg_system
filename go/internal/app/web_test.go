package app

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// The landing page a notification taps into carries the documented tt://
// address, plus the compact userinfo form for a client that prefers it. A
// malformed link is refused instead of rendered.
func TestOpenPageOffersBothTTURLs(t *testing.T) {
	t.Setenv("TEAMTALK_HOST", "example.org")
	srv := NewServer(Load(), nil, nil)

	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/open?u=denizsincar29&p=c2VjcmV0", nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	body := rec.Body.String()
	// The primary address is the documented shape from BearWare's "tt Files and
	// tt:// URLs": ports are query parameters, never the authority. The compact
	// userinfo form stays as the second button.
	for _, want := range []string{
		"tt://example.org?tcpport=10333&amp;udpport=10333&amp;encrypted=false&amp;username=denizsincar29&amp;password=secret",
		"tt://denizsincar29:secret@example.org:10333:10333/",
	} {
		if !strings.Contains(body, want) {
			t.Errorf("page does not contain %q\n%s", want, body)
		}
	}

	rec = httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/open?u=&p=", nil))
	if rec.Code != http.StatusBadRequest {
		t.Errorf("empty link status = %d, want 400", rec.Code)
	}
}

// A deployment on non-default ports says so in the query — the address stays
// the documented shape whatever the ports are.
func TestOpenPageCarriesConfiguredPorts(t *testing.T) {
	t.Setenv("TEAMTALK_HOST", "example.org")
	t.Setenv("TEAMTALK_TCP_PORT", "10340")
	t.Setenv("TEAMTALK_UDP_PORT", "10341")
	srv := NewServer(Load(), nil, nil)

	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/open?u=denizsincar29&p=c2VjcmV0", nil))
	if want := "tt://example.org?tcpport=10340&amp;udpport=10341&amp;"; !strings.Contains(rec.Body.String(), want) {
		t.Errorf("page does not contain %q\n%s", want, rec.Body.String())
	}
}

// The tap target of a "new registration" push: the admin dashboard opened on
// that account, not the tt:// address the other notifications carry.
func TestAdminAccountURL(t *testing.T) {
	t.Setenv("TEAMTALK_HOST", "example.org")
	cfg := Load()
	if got, want := adminAccountURL(cfg, "denizsincar29"), "https://tt.example.org/admin/?account=denizsincar29"; got != want {
		t.Errorf("adminAccountURL = %q, want %q", got, want)
	}
	// A name the dashboard has to be told about verbatim travels escaped.
	if got, want := adminAccountURL(cfg, "a b"), "https://tt.example.org/admin/?account=a+b"; got != want {
		t.Errorf("adminAccountURL = %q, want %q", got, want)
	}
}

// An unauthenticated deep link hands its query to the login form, so the
// dashboard still opens on the account after the password is entered.
func TestAdminGuardKeepsDeepLink(t *testing.T) {
	t.Setenv("TEAMTALK_HOST", "example.org")
	srv := NewServer(Load(), nil, nil)

	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/admin/?account=denizsincar29", nil))
	if rec.Code != http.StatusFound {
		t.Fatalf("status = %d, want 302", rec.Code)
	}
	if got, want := rec.Header().Get("Location"), "/admin/login?next=%2Fadmin%2F%3Faccount%3Ddenizsincar29"; got != want {
		t.Errorf("Location = %q, want %q", got, want)
	}

	// The login form renders that address as a hidden field, and only /admin
	// paths are ever let through.
	rec = httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/admin/login?next=%2Fadmin%2F%3Faccount%3Ddenizsincar29", nil))
	if body := rec.Body.String(); !strings.Contains(body, `name="next" value="/admin/?account=denizsincar29"`) {
		t.Errorf("login page does not carry the deep link\n%s", body)
	}
	for _, bad := range []string{"https://evil.example/", "//evil.example/", "/etc/passwd", "/admin/../etc"} {
		if got := safeNext(bad); got != "" {
			t.Errorf("safeNext(%q) = %q, want empty", bad, got)
		}
	}
}
