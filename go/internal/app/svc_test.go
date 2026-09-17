package app

import (
	"regexp"
	"testing"
	"time"
)

// The notification clock is meant to read as "15:32 МСК": four digits, a colon
// and the zone label. A wrong time (UTC from a databaseless container, say)
// would not show up in any other test, so the shape and the offset are pinned
// here.
func TestMskClock(t *testing.T) {
	got := mskClock()
	if !regexp.MustCompile(`^\d\d:\d\d МСК$`).MatchString(got) {
		t.Fatalf("mskClock() = %q, want HH:MM МСК", got)
	}
	if mskZone.Offset() != 3*60*60 {
		t.Fatalf("mskZone offset = %d, want 10800", mskZone.Offset())
	}
	// The rendered time must be Moscow wall time, not the process's own zone.
	want := time.Now().In(time.FixedZone("test", 3*60*60)).Format("15:04") + " МСК"
	if got != want {
		t.Fatalf("mskClock() = %q, want %q", got, want)
	}
}
