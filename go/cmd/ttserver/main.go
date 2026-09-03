// Command ttserver is the single Go process that replaces the Python
// registration system + ttbot worker: it runs the TeamTalk bot in-process,
// serves the public registration pages and the admin panel, and persists the
// scheduler tasks like the old file-based scheduler did.
package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/denizsincar29/teamtalk_reg_system/go/internal/app"
)

func main() {
	cfg := app.Load()

	svc := app.NewService(cfg)
	svc.Start()

	sched := app.NewScheduler(svc, cfg.DataDir)
	sched.Start()

	srv := app.NewServer(cfg, svc, sched)
	httpSrv := &http.Server{
		Addr:              cfg.ListenAddr,
		Handler:           srv.Handler(),
		ReadHeaderTimeout: 10 * time.Second,
	}

	go func() {
		log.Printf("ttserver: listening on %s (bot %s@%s:%d)",
			cfg.ListenAddr, cfg.BotUsername, cfg.BotHost, cfg.TCPPort)
		if err := httpSrv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("ttserver: %v", err)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)
	<-stop
	log.Println("ttserver: shutting down")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	sched.Stop()
	svc.Stop()
	_ = httpSrv.Shutdown(ctx)
}
