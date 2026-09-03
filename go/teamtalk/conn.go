package teamtalk

import (
	"bufio"
	"errors"
	"fmt"
	"net"
	"strings"
	"sync"
	"time"
)

// Client is a minimal text-protocol TeamTalk TCP connection.
type Client struct {
	conn net.Conn
	br   *bufio.Reader
	mu   sync.Mutex // guards conn writes

	cmdid int

	// ReadTimeout is refreshed before every line read while waiting for a
	// server reply.
	ReadTimeout time.Duration
}

// Dial connects to a TeamTalk server command port.
func Dial(host string, port int) (*Client, error) {
	addr := net.JoinHostPort(host, fmt.Sprint(port))
	conn, err := net.DialTimeout("tcp", addr, 10*time.Second)
	if err != nil {
		return nil, err
	}
	return &Client{conn: conn, br: bufio.NewReader(conn), ReadTimeout: 30 * time.Second}, nil
}

// NextCmdID returns the next command id for this connection.
func (c *Client) NextCmdID() int {
	c.cmdid++
	return c.cmdid
}

// Send writes one raw command line to the server.
func (c *Client) Send(line string) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	_, err := c.conn.Write([]byte(line))
	return err
}

// ReadLine returns the next parsed server line. A read timeout is returned as
// ErrTimeout so callers can tell a silent server apart from a closed one.
func (c *Client) ReadLine() (Line, error) {
	for {
		_ = c.conn.SetReadDeadline(time.Now().Add(c.ReadTimeout))
		raw, err := c.br.ReadString('\n')
		if err != nil {
			if ne, ok := err.(net.Error); ok && ne.Timeout() {
				return Line{}, ErrTimeout
			}
			return Line{}, err
		}
		line := ParseLine(raw)
		if line.Cmd == "" && len(line.Vars) == 0 {
			continue
		}
		return line, nil
	}
}

// Close closes the connection.
func (c *Client) Close() error { return c.conn.Close() }

// ErrTimeout is returned when the server does not answer within ReadTimeout.
var ErrTimeout = errors.New("timeout waiting for server reply")

// Exec sends a command carrying cmdid and reads lines synchronously until the
// matching "end id=<cmdid>" terminator. Returns every line received in
// between, in order. Convenient for one-shot probes; event-driven use should
// go through Bot instead.
func (c *Client) Exec(line string, cmdid int) ([]Line, error) {
	if err := c.Send(line); err != nil {
		return nil, err
	}
	var lines []Line
	for {
		l, err := c.ReadLine()
		if err != nil {
			return lines, err
		}
		lines = append(lines, l)
		if l.Cmd == SrvEndCmd && l.Int(KeyCmdID) == cmdid {
			return lines, nil
		}
	}
}

// Summary renders lines compactly for logging (never prints passwords).
func Summary(lines []Line) string {
	parts := make([]string, 0, len(lines))
	for _, l := range lines {
		var b strings.Builder
		b.WriteString(l.Cmd)
		for k, v := range l.Vars {
			if k == KeyPassword || k == KeyOpPassword {
				continue
			}
			b.WriteString(" " + k + "=" + v)
		}
		parts = append(parts, b.String())
	}
	return strings.Join(parts, " | ")
}
