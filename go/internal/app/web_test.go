package app

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// The landing page a notification taps into has to carry both tt:// shapes:
// which one a client opens is documented nowhere, so the owner taps until one
// works. A malformed link is refused instead of rendered.
func TestOpenPageOffersBothTTURLs(t *testing.T) {
	t.Setenv("TEAMTALK_HOST", "example.org")
	srv := NewServer(Load(), nil, nil)

	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/open?u=denizsincar29&p=c2VjcmV0", nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	body := rec.Body.String()
	for _, want := range []string{
		"tt://example.org:10333:10333/?username=denizsincar29&amp;password=secret",
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
