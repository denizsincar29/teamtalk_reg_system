package app

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"time"
)

// notify posts a push notification to the ntfy topic (fire-and-forget in its
// own goroutine, so it never blocks the bot's read loop or an HTTP handler).
// An empty url silently disables notifications, mirroring the Python ntfy.py.
// If NTFY_USERNAME/NTFY_PASSWORD are set for the process, requests carry HTTP
// basic auth (the deployment's ntfy server is protected, like the Python bot).
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
		req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(body))
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
