package app

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

// notify posts a push notification to the ntfy topic (fire-and-forget in its
// own goroutine, so it never blocks the bot's read loop or an HTTP handler).
// An empty url silently disables notifications, mirroring the Python ntfy.py.
// If NTFY_USERNAME/NTFY_PASSWORD are set for the process, requests carry HTTP
// basic auth (the deployment's ntfy server is protected, like the Python bot).
//
// The url comes from .env built as server + "/" + topic, i.e. with the topic in
// the path. But ntfy only parses a JSON body when it is POSTed to the SERVER
// ROOT: the topic then has to travel inside the body as "topic". With the topic
// in the address ntfy treats the body as plain text and stores it in "message"
// verbatim — which is how the raw JSON ended up on the lock screen instead of a
// title and a text. So the address is split here: scheme and host go to the
// request, the last path segment goes into the body.
func notify(rawURL, title, message string, tags []string, priority int) {
	if rawURL == "" {
		return
	}
	endpoint, topic := splitTopic(rawURL)
	if topic == "" {
		log.Printf("ntfy: no topic in %q, notification not sent", rawURL)
		return
	}
	go func() {
		payload := map[string]any{
			"topic":    topic,
			"title":    title,
			"message":  message,
			"priority": priority,
		}
		if len(tags) > 0 {
			payload["tags"] = tags
		}
		body, err := json.Marshal(payload)
		if err != nil {
			return
		}
		req, err := http.NewRequest(http.MethodPost, endpoint, bytes.NewReader(body))
		if err != nil {
			return
		}
		req.Header.Set("Content-Type", "application/json")
		if u := os.Getenv("NTFY_USERNAME"); u != "" {
			req.SetBasicAuth(u, os.Getenv("NTFY_PASSWORD"))
		}
		client := &http.Client{Timeout: 5 * time.Second}
		resp, err := client.Do(req)
		if err != nil {
			log.Printf("ntfy: %v", err)
			return
		}
		resp.Body.Close()
	}()
}

// splitTopic splits a configured ntfy address into the endpoint to POST to (the
// server root) and the topic to put into the body. Query parameters are kept —
// ntfy accepts credentials there — but the path always collapses to "/": JSON
// publishing is only understood at the root, so a topic URL cannot be used
// as-is. An address without a topic yields an empty topic, and the caller stays
// silent rather than posting somewhere the message would be lost.
func splitTopic(rawURL string) (endpoint, topic string) {
	u, err := url.Parse(rawURL)
	if err != nil || u.Host == "" {
		return rawURL, ""
	}
	if parts := strings.Split(strings.Trim(u.Path, "/"), "/"); len(parts) > 0 {
		topic = parts[len(parts)-1]
	}
	u.Path, u.Fragment = "/", ""
	return u.String(), topic
}
