package app

import (
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// Without a configured policy the registration form has no consent step at
// all — neither the checkbox nor the link.
func TestIndexWithoutPolicyHasNoConsent(t *testing.T) {
	t.Setenv("TEAMTALK_HOST", "example.org")
	srv := NewServer(Load(), nil, nil)

	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))
	body := rec.Body.String()
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	for _, unwanted := range []string{"name=\"consent\"", "Политика обработки персональных данных"} {
		if strings.Contains(body, unwanted) {
			t.Errorf("page without a policy contains %q\n%s", unwanted, body)
		}
	}
}

// PRIVACY_URL puts the operator's own policy link on the form.
func TestIndexWithPolicyURL(t *testing.T) {
	t.Setenv("TEAMTALK_HOST", "example.org")
	t.Setenv("PRIVACY_URL", "https://example.net/privacy")
	srv := NewServer(Load(), nil, nil)

	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))
	body := rec.Body.String()
	for _, want := range []string{"name=\"consent\"", "href=\"https://example.net/privacy\""} {
		if !strings.Contains(body, want) {
			t.Errorf("page does not contain %q\n%s", want, body)
		}
	}
}

// PRIVACY_FILE is served at /privacy and linked from the form; the file is
// read per request, so an edit needs no restart.
func TestIndexWithPolicyFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "privacy.txt")
	if err := os.WriteFile(path, []byte("Политика версии 1"), 0o644); err != nil {
		t.Fatal(err)
	}
	t.Setenv("TEAMTALK_HOST", "example.org")
	t.Setenv("PRIVACY_FILE", path)
	srv := NewServer(Load(), nil, nil)

	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))
	if body := rec.Body.String(); !strings.Contains(body, "href=\"/privacy\"") {
		t.Errorf("form does not link /privacy\n%s", body)
	}

	rec = httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/privacy", nil))
	if body := rec.Body.String(); rec.Code != http.StatusOK || !strings.Contains(body, "Политика версии 1") {
		t.Errorf("/privacy = %d %q", rec.Code, body)
	}

	if err := os.WriteFile(path, []byte("Политика версии 2"), 0o644); err != nil {
		t.Fatal(err)
	}
	rec = httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/privacy", nil))
	if body := rec.Body.String(); !strings.Contains(body, "Политика версии 2") {
		t.Errorf("/privacy is not read per request: %q", body)
	}
}

// With a policy configured the checkbox is still required: a registration
// without it is refused before anything touches the TeamTalk server.
func TestRegisterRequiresConsentWhenPolicySet(t *testing.T) {
	t.Setenv("TEAMTALK_HOST", "example.org")
	t.Setenv("PRIVACY_URL", "https://example.net/privacy")
	srv := NewServer(Load(), nil, nil)

	form := url.Values{"username": {"newuser"}, "password": {"secret"}}
	req := httptest.NewRequest(http.MethodPost, "/register", strings.NewReader(form.Encode()))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	rec := httptest.NewRecorder()
	srv.Handler().ServeHTTP(rec, req)
	if body := rec.Body.String(); !strings.Contains(body, "Нужно согласие") {
		t.Errorf("registration without consent was not refused\n%s", body)
	}
}

// The account note carries the policy link unless the operator supplies the
// wording; with no policy there is no note to write.
func TestConsentNote(t *testing.T) {
	s := &Service{cfg: Config{PrivacyURL: "https://example.net/privacy"}}
	if got := s.consentNote(); !strings.Contains(got, "https://example.net/privacy") {
		t.Errorf("note = %q, want the policy link", got)
	}

	s = &Service{cfg: Config{PrivacyFile: "/tmp/p.txt", ShortHost: "tt.example.org"}}
	if got := s.consentNote(); !strings.Contains(got, "https://tt.example.org/privacy") {
		t.Errorf("note = %q, want the absolute /privacy link", got)
	}

	s = &Service{cfg: Config{PrivacyURL: "https://example.net/privacy", ConsentNote: "Своя формулировка"}}
	if got := s.consentNote(); got != "Своя формулировка" {
		t.Errorf("note = %q, want the operator's wording", got)
	}

	s = &Service{cfg: Config{}}
	if got := s.consentNote(); got != "" {
		t.Errorf("note = %q, want empty without a policy", got)
	}
}
