package app

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"time"
)

// notify posts a push notification to the ntfy topic (fire-and-forget in its
// own goroutine, so it never blocks the bot's read loop or an HTTP handler).
// An empty url silently disables notifications, mirroring the Python ntfy.py.
func notify(url, title, message string, tags []string, priority int) {
	if url == "" {
		return
	}
	go func() {
		payload := map[string]any{
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
		client := &http.Client{Timeout: 5 * time.Second}
		resp, err := client.Post(url, "application/json", bytes.NewReader(body))
		if err != nil {
			log.Printf("ntfy: %v", err)
			return
		}
		resp.Body.Close()
	}()
}
