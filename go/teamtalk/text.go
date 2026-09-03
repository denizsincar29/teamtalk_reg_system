package teamtalk

import (
	"strings"
)

// Line is one server line: a command name plus parsed properties. Every value
// (numbers included) is stored as a raw string; use Int for numeric access.
type Line struct {
	Cmd  string
	Vars map[string]string
}

// Int returns the integer value of a property (0 when absent or non-numeric).
func (l Line) Int(key string) int {
	v, ok := l.Vars[key]
	if !ok {
		return 0
	}
	out := 0
	neg := false
	for i := 0; i < len(v); i++ {
		c := v[i]
		switch {
		case c == '-' && i == 0:
			neg = true
		case c >= '0' && c <= '9':
			out = out*10 + int(c-'0')
		default:
			return 0
		}
	}
	if neg {
		return -out
	}
	return out
}

// Str returns the string value of a property (empty when absent).
func (l Line) Str(key string) string { return l.Vars[key] }

// Has reports whether a property is present.
func (l Line) Has(key string) bool {
	_, ok := l.Vars[key]
	return ok
}

// unescape reverses the client-side escaping (\n \r \" \\ back to characters).
// Mirrors RebuildString in Commands.cpp.
func unescape(s string) string {
	if !strings.ContainsRune(s, '\\') {
		return s
	}
	var b strings.Builder
	b.Grow(len(s))
	for i := 0; i < len(s); i++ {
		if s[i] == '\\' && i+1 < len(s) {
			switch s[i+1] {
			case 'n':
				b.WriteByte('\n')
				i++
				continue
			case 'r':
				b.WriteByte('\r')
				i++
				continue
			case '"':
				b.WriteByte('"')
				i++
				continue
			case '\\':
				b.WriteByte('\\')
				i++
				continue
			}
		}
		b.WriteByte(s[i])
	}
	return b.String()
}

// ParseLine splits one server line into command and properties, following
// ExtractProperties semantics in Commands.cpp: values are either "quoted"
// (backslash-escaped), [comma,lists] or bare tokens.
func ParseLine(line string) Line {
	line = strings.TrimSuffix(strings.TrimSuffix(line, "\n"), "\r")
	res := Line{Vars: map[string]string{}}

	sp := strings.IndexByte(line, ' ')
	if sp < 0 {
		res.Cmd = line
		return res
	}
	res.Cmd = line[:sp]
	i := sp
	n := len(line)

	for i < n {
		for i < n && (line[i] == ' ' || line[i] == '\t') {
			i++
		}
		if i >= n {
			break
		}
		start := i
		for i < n && line[i] != ' ' && line[i] != '=' {
			i++
		}
		if i >= n || line[i] != '=' {
			break
		}
		name := line[start:i]
		i++ // past '='
		for i < n && line[i] == ' ' {
			i++
		}
		if i >= n {
			break
		}
		var val string
		switch line[i] {
		case '"':
			i++ // past opening quote
			var b strings.Builder
			for i < n {
				if line[i] == '\\' && i+1 < n {
					b.WriteByte(line[i])
					b.WriteByte(line[i+1])
					i += 2
					continue
				}
				if line[i] == '"' {
					i++
					break
				}
				b.WriteByte(line[i])
				i++
			}
			val = unescape(b.String())
		case '[':
			i++
			if end := strings.IndexByte(line[i:], ']'); end >= 0 {
				val = line[i : i+end]
				i += end + 1
			} else {
				val = line[i:]
				i = n
			}
		default:
			start := i
			for i < n && line[i] != ' ' {
				i++
			}
			val = line[start:i]
		}
		res.Vars[name] = val
	}
	return res
}
