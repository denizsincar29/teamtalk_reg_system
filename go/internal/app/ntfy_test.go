package app

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestSplitTopic(t *testing.T) {
	cases := []struct{ in, endpoint, topic string }{
		{"https://push.denizsincar.ru/teamtalk", "https://push.denizsincar.ru/", "teamtalk"},
		{"https://push.denizsincar.ru/", "https://push.denizsincar.ru/", ""},
		{"https://push.denizsincar.ru", "https://push.denizsincar.ru/", ""},
		{"https://push.denizsincar.ru/ntfy/teamtalk", "https://push.denizsincar.ru/", "teamtalk"},
		{"https://push.denizsincar.ru/teamtalk?auth=token", "https://push.denizsincar.ru/?auth=token", "teamtalk"},
	}
	for _, c := range cases {
		endpoint, topic := splitTopic(c.in)
		if endpoint != c.endpoint || topic != c.topic {
			t.Errorf("splitTopic(%q) = (%q, %q), want (%q, %q)", c.in, endpoint, topic, c.endpoint, c.topic)
		}
	}
}

// The address from .env must turn into a request to the server root with the
// topic inside the body: otherwise ntfy does not parse the JSON and the lock
// screen shows the raw payload instead of the title and the text.
func TestNotifyPostsToRootWithTopicInBody(t *testing.T) {
	type sent struct {
		path       string
		contentTyp string
		body       map[string]any
	}
	got := make(chan sent, 1)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var body map[string]any
		_ = json.NewDecoder(r.Body).Decode(&body)
		got <- sent{path: r.URL.Path, contentTyp: r.Header.Get("Content-Type"), body: body}
	}))
	defer srv.Close()

	const click = "tt://bot:secret@denizsincar.ru:10333:10333/"
	notify(srv.URL+"/teamtalk", click, "User connected", "vinograd joined the server", []string{"green_circle"}, 3)

	select {
	case s := <-got:
		if s.path != "/" {
			t.Errorf("posted to %q, want the root \"/\"", s.path)
		}
		if s.contentTyp != "application/json" {
			t.Errorf("Content-Type %q, want application/json", s.contentTyp)
		}
		if s.body["topic"] != "teamtalk" {
			t.Errorf("topic = %v, want teamtalk", s.body["topic"])
		}
		if s.body["click"] != click {
			t.Errorf("click = %v, want %q", s.body["click"], click)
		}
		if s.body["title"] != "User connected" || s.body["message"] != "vinograd joined the server" {
			t.Errorf("title/message got mangled: %v", s.body)
		}
		if p, ok := s.body["priority"].(float64); !ok || p != 3 {
			t.Errorf("priority = %v, want 3", s.body["priority"])
		}
	case <-time.After(3 * time.Second):
		t.Fatal("no request was sent")
	}
}
