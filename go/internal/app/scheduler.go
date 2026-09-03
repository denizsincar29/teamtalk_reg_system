package app

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// Task types, mirroring the Python scheduler's TaskType.
const (
	TaskBroadcast      = "broadcast"
	TaskChannelMessage = "channel_message"
	TaskCreateChannel  = "create_channel"
	TaskPMOnline       = "pm_online"
	TaskOnUserLogin    = "on_user_login"
	TaskStatusChange   = "status_change"
)

type task struct {
	ID               string `json:"id"`
	Type             string `json:"type"`
	Name             string `json:"name"`
	Message          string `json:"message"`
	ChannelID        int    `json:"channel_id"`
	ChannelName      string `json:"channel_name"`
	ChannelPassword  string `json:"channel_password"`
	ScheduledTime    string `json:"scheduled_time"`
	TargetUsername   string `json:"target_username"`
	DelayMinSeconds  int    `json:"delay_min_seconds"`
	DelayMaxSeconds  int    `json:"delay_max_seconds"`
	StatusMode       int    `json:"status_mode"`
	RecurringMinutes int    `json:"recurring_minutes"`
	Enabled          bool   `json:"enabled"`
	CreatedAt        string `json:"created_at"`
	LastRun          string `json:"last_run"`
	NextRun          string `json:"next_run"`
}

type offlinePM struct {
	Message  string `json:"message"`
	TaskName string `json:"task_name"`
	QueuedAt string `json:"queued_at"`
}

// Scheduler persists scheduled tasks and the offline-PM queue as JSON files
// and fires due tasks on a 30s tick. Persistence lives under the data dir, so
// tasks survive restarts exactly like the Python file-based scheduler.
type Scheduler struct {
	svc     *Service
	dataDir string

	mu      sync.Mutex
	tasks   map[string]task
	offline map[string][]offlinePM
	done    chan struct{}
	started bool
}

func NewScheduler(svc *Service, dataDir string) *Scheduler {
	sch := &Scheduler{
		svc:     svc,
		dataDir: dataDir,
		tasks:   make(map[string]task),
		offline: make(map[string][]offlinePM),
		done:    make(chan struct{}),
	}
	svc.sched = sch
	return sch
}

func (sch *Scheduler) taskFile() string { return filepath.Join(sch.dataDir, "scheduled_tasks.json") }
func (sch *Scheduler) pmFile() string   { return filepath.Join(sch.dataDir, "offline_pm_queue.json") }

func (sch *Scheduler) Start() {
	sch.load()
	sch.mu.Lock()
	already := sch.started
	sch.started = true
	sch.mu.Unlock()
	if already {
		return
	}
	go sch.tick()
}

func (sch *Scheduler) Stop() {
	close(sch.done)
}

func (sch *Scheduler) load() {
	sch.mu.Lock()
	defer sch.mu.Unlock()
	_ = os.MkdirAll(sch.dataDir, 0o755)
	if raw, err := os.ReadFile(sch.taskFile()); err == nil && len(raw) > 0 {
		if err := json.Unmarshal(raw, &sch.tasks); err != nil {
			log.Printf("scheduler: bad tasks file: %v", err)
		}
	}
	if raw, err := os.ReadFile(sch.pmFile()); err == nil && len(raw) > 0 {
		if err := json.Unmarshal(raw, &sch.offline); err != nil {
			log.Printf("scheduler: bad offline-pm file: %v", err)
		}
	}
}

func (sch *Scheduler) saveLocked() {
	_ = os.MkdirAll(sch.dataDir, 0o755)
	if b, err := json.MarshalIndent(sch.tasks, "", "  "); err == nil {
		_ = os.WriteFile(sch.taskFile(), b, 0o644)
	}
	if b, err := json.MarshalIndent(sch.offline, "", "  "); err == nil {
		_ = os.WriteFile(sch.pmFile(), b, 0o644)
	}
}

func (sch *Scheduler) tick() {
	t := time.NewTicker(30 * time.Second)
	defer t.Stop()
	for {
		select {
		case <-sch.done:
			return
		case <-t.C:
			sch.runDue()
		}
	}
}

func (sch *Scheduler) runDue() {
	now := time.Now()
	sch.mu.Lock()
	var due []task
	for id, tk := range sch.tasks {
		if !tk.Enabled || tk.NextRun == "" {
			continue
		}
		next, ok := parseTaskTime(tk.NextRun)
		if ok && !now.Before(next) {
			cp := tk
			cp.ID = id
			due = append(due, cp)
		}
	}
	sch.mu.Unlock()

	for _, tk := range due {
		ok := sch.execute(tk)
		sch.mu.Lock()
		cur, exists := sch.tasks[tk.ID]
		if !exists {
			sch.mu.Unlock()
			continue
		}
		cur.LastRun = nowLocalStr()
		if cur.RecurringMinutes > 0 {
			cur.NextRun = time.Now().Add(time.Duration(cur.RecurringMinutes) * time.Minute).Format(isoLayout)
		} else {
			// One-time tasks are spent after their single attempt (Python parity).
			cur.Enabled = false
			cur.NextRun = ""
		}
		sch.tasks[tk.ID] = cur
		sch.saveLocked()
		sch.mu.Unlock()
		_ = ok
	}
}

func (sch *Scheduler) execute(tk task) error {
	switch tk.Type {
	case TaskBroadcast:
		if tk.Message == "" {
			return errNoMessage
		}
		return sch.svc.SendBroadcast(tk.Message)
	case TaskChannelMessage:
		if tk.Message == "" {
			return errNoMessage
		}
		if tk.ChannelID > 0 {
			cur, err := sch.svc.CurrentChannel()
			if err != nil {
				return err
			}
			if cur != tk.ChannelID {
				if err := sch.svc.JoinChannel(tk.ChannelID); err != nil {
					return err
				}
				time.Sleep(500 * time.Millisecond)
			}
		}
		return sch.svc.SendChannelMessage(tk.Message)
	case TaskPMOnline:
		if tk.TargetUsername == "" || tk.Message == "" {
			return errNoTarget
		}
		users, err := sch.svc.Users()
		if err != nil {
			return err
		}
		for _, u := range users {
			if strings.EqualFold(u.Username, tk.TargetUsername) {
				return sch.svc.SendPrivateMessage(u.ID, tk.Message)
			}
		}
		return nil // user offline: skip silently (Python returns success)
	case TaskStatusChange:
		return sch.svc.SetStatus(logicalToFlag(tk.StatusMode), tk.Message)
	case TaskCreateChannel:
		return errNotImplemented
	}
	return errUnknownType
}

var (
	errNoMessage      = errX("no message")
	errNoTarget       = errX("no target username")
	errNotImplemented = errX("not implemented")
	errUnknownType    = errX("unknown task type")
)

type errX string

func (e errX) Error() string { return string(e) }

func (sch *Scheduler) Tasks() []task {
	sch.mu.Lock()
	defer sch.mu.Unlock()
	out := make([]task, 0, len(sch.tasks))
	for _, t := range sch.tasks {
		out = append(out, t)
	}
	return out
}

func (sch *Scheduler) GetTask(id string) (task, bool) {
	sch.mu.Lock()
	defer sch.mu.Unlock()
	t, ok := sch.tasks[id]
	return t, ok
}

func (sch *Scheduler) AddTask(taskType, name, message string, channelID int, scheduledTime string, recurringMinutes int, targetUsername string, delayMin, delayMax, statusMode int) (string, error) {
	id := randID()
	tk := task{
		ID:               id,
		Type:             taskType,
		Name:             name,
		Message:          message,
		ChannelID:        channelID,
		ScheduledTime:    scheduledTime,
		TargetUsername:   targetUsername,
		DelayMinSeconds:  delayMin,
		DelayMaxSeconds:  delayMax,
		StatusMode:       statusMode,
		RecurringMinutes: recurringMinutes,
		Enabled:          true,
		CreatedAt:        nowLocalStr(),
	}
	if t, ok := parseTaskTime(scheduledTime); ok && !scheduledTimeDateEmpty(scheduledTime) {
		tk.NextRun = t.Format(isoLayout)
	} else if recurringMinutes > 0 {
		tk.NextRun = time.Now().Add(time.Duration(recurringMinutes) * time.Minute).Format(isoLayout)
	}
	sch.mu.Lock()
	sch.tasks[id] = tk
	sch.saveLocked()
	sch.mu.Unlock()
	return id, nil
}

func (sch *Scheduler) UpdateTask(id string, patch map[string]any) bool {
	sch.mu.Lock()
	tk, ok := sch.tasks[id]
	if !ok {
		sch.mu.Unlock()
		return false
	}
	applyPatch(&tk, patch)
	sch.tasks[id] = tk
	sch.saveLocked()
	sch.mu.Unlock()
	return true
}

func applyPatch(tk *task, patch map[string]any) {
	if v, ok := patch["name"]; ok {
		tk.Name, _ = v.(string)
	}
	if v, ok := patch["message"]; ok {
		tk.Message, _ = v.(string)
	}
	if v, ok := patch["channel_id"]; ok {
		tk.ChannelID = toInt(v)
	}
	if v, ok := patch["scheduled_time"]; ok {
		if s, _ := v.(string); s == "" {
			tk.ScheduledTime = ""
		} else {
			tk.ScheduledTime = s
		}
	}
	if v, ok := patch["recurring_minutes"]; ok {
		tk.RecurringMinutes = toInt(v)
	}
	if v, ok := patch["enabled"]; ok {
		tk.Enabled, _ = v.(bool)
	}
	if v, ok := patch["target_username"]; ok {
		tk.TargetUsername, _ = v.(string)
	}
	if v, ok := patch["delay_min_seconds"]; ok {
		tk.DelayMinSeconds = toInt(v)
	}
	if v, ok := patch["delay_max_seconds"]; ok {
		tk.DelayMaxSeconds = toInt(v)
	}
	if v, ok := patch["status_mode"]; ok {
		tk.StatusMode = toInt(v)
	}
	if v, ok := patch["scheduled_time"]; ok {
		_ = v // handled above
	}
	// Recompute next run from the new schedule.
	if t, ok := parseTaskTime(tk.ScheduledTime); ok && tk.ScheduledTime != "" {
		tk.NextRun = t.Format(isoLayout)
	} else if tk.RecurringMinutes > 0 {
		tk.NextRun = time.Now().Add(time.Duration(tk.RecurringMinutes) * time.Minute).Format(isoLayout)
	} else {
		tk.NextRun = ""
	}
}

func toInt(v any) int {
	switch n := v.(type) {
	case int:
		return n
	case int64:
		return int(n)
	case float64:
		return int(n)
	}
	return 0
}

func (sch *Scheduler) DeleteTask(id string) bool {
	sch.mu.Lock()
	defer sch.mu.Unlock()
	if _, ok := sch.tasks[id]; !ok {
		return false
	}
	delete(sch.tasks, id)
	sch.saveLocked()
	return true
}

func (sch *Scheduler) ToggleTask(id string) bool {
	sch.mu.Lock()
	defer sch.mu.Unlock()
	tk, ok := sch.tasks[id]
	if !ok {
		return false
	}
	tk.Enabled = !tk.Enabled
	sch.tasks[id] = tk
	sch.saveLocked()
	return true
}

func (sch *Scheduler) RunNow(id string) error {
	tk, ok := sch.GetTask(id)
	if !ok {
		return errUnknownType
	}
	return sch.execute(tk)
}

// OnUserLogin delivers queued offline PMs and fires on_user_login tasks. It is
// called from the service's own goroutine when a user comes online.
func (sch *Scheduler) OnUserLogin(username string, userID int) {
	delivered := sch.takeOfflinePMs(username, userID)

	sch.mu.Lock()
	var targets []task
	for _, tk := range sch.tasks {
		if !tk.Enabled || tk.Type != TaskOnUserLogin {
			continue
		}
		if tk.TargetUsername != "" && !strings.EqualFold(tk.TargetUsername, username) {
			continue
		}
		targets = append(targets, tk)
	}
	sch.mu.Unlock()
	_ = delivered

	for _, tk := range targets {
		go sch.fireLoginTask(tk, userID)
	}
}

func (sch *Scheduler) takeOfflinePMs(username string, userID int) int {
	key := strings.ToLower(username)
	sch.mu.Lock()
	pms := sch.offline[key]
	delete(sch.offline, key)
	if len(pms) > 0 {
		sch.saveLocked()
	}
	sch.mu.Unlock()

	n := 0
	for _, pm := range pms {
		if err := sch.svc.SendPrivateMessage(userID, pm.Message); err == nil {
			n++
		}
	}
	return n
}

func (sch *Scheduler) fireLoginTask(tk task, userID int) {
	if tk.DelayMaxSeconds > tk.DelayMinSeconds {
		d := tk.DelayMinSeconds
		if span := tk.DelayMaxSeconds - tk.DelayMinSeconds; span > 0 {
			d += randN(span)
		}
		time.Sleep(time.Duration(d) * time.Second)
	} else if tk.DelayMinSeconds > 0 {
		time.Sleep(time.Duration(tk.DelayMinSeconds) * time.Second)
	}
	if tk.Message == "" {
		return
	}
	_ = sch.svc.SendPrivateMessage(userID, tk.Message)
}

func (sch *Scheduler) QueueOfflinePM(username, message, taskName string) {
	key := strings.ToLower(username)
	sch.mu.Lock()
	sch.offline[key] = append(sch.offline[key], offlinePM{
		Message: message, TaskName: taskName, QueuedAt: nowLocalStr(),
	})
	sch.saveLocked()
	sch.mu.Unlock()
}

func (sch *Scheduler) OfflinePMQueue() map[string][]offlinePM {
	sch.mu.Lock()
	defer sch.mu.Unlock()
	out := make(map[string][]offlinePM, len(sch.offline))
	for k, v := range sch.offline {
		out[k] = append([]offlinePM(nil), v...)
	}
	return out
}

func (sch *Scheduler) ClearOfflinePM(username string) bool {
	key := strings.ToLower(username)
	sch.mu.Lock()
	defer sch.mu.Unlock()
	if _, ok := sch.offline[key]; !ok {
		return false
	}
	delete(sch.offline, key)
	sch.saveLocked()
	return true
}

// ---- time helpers ----

const isoLayout = "2006-01-02T15:04:05"

func nowLocalStr() string { return time.Now().Format(isoLayout) }

// parseTaskTime accepts the timestamp forms the UI and the legacy Python data
// files can carry. Naive (zone-less) timestamps are read in local time, which
// is what the old app produced and compared against.
func parseTaskTime(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, false
	}
	layouts := []string{
		time.RFC3339,
		"2006-01-02T15:04:05.999999999Z07:00",
		"2006-01-02T15:04:05.999999999",
		isoLayout,
		"2006-01-02 15:04:05",
		"2006-01-02",
	}
	for _, l := range layouts {
		if t, err := time.ParseInLocation(l, s, time.Local); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

func scheduledTimeDateEmpty(s string) bool {
	// The UI sends a bare date ("2026-09-03") when no clock time was picked.
	_, err := time.ParseInLocation("2006-01-02", strings.TrimSpace(s), time.Local)
	return err == nil
}

func randID() string {
	var b [4]byte
	if _, err := rand.Read(b[:]); err != nil {
		return time.Now().Format("150405")
	}
	return hex.EncodeToString(b[:])
}

func randN(n int) int {
	// n > 0 by the caller; a cheap uniform sample is enough for a delay.
	return int(time.Now().UnixNano()%int64(n)) + 0
}
