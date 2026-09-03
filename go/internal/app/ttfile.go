package app

import (
	"fmt"
	"strings"
)

// ttFileXML renders a TeamTalk 5 client .tt file in the same XML shape the
// Python system produced (see app/tt_file.py). username/password are escaped
// for XML text.
func ttFileXML(cfg Config, username, password string) string {
	name := cfg.PublicHost + " - " + username
	var b strings.Builder
	b.WriteString(`<?xml version="1.0" encoding="UTF-8"?>` + "\n")
	b.WriteString(`<teamtalk version="5.0">` + "\n")
	b.WriteString("  <host>\n")
	fmt.Fprintf(&b, "    <name>%s</name>\n", xmlEsc(name))
	fmt.Fprintf(&b, "    <address>%s</address>\n", xmlEsc(cfg.PublicHost))
	fmt.Fprintf(&b, "    <tcpport>%d</tcpport>\n", cfg.TCPPort)
	fmt.Fprintf(&b, "    <udpport>%d</udpport>\n", cfg.UDPPort)
	b.WriteString("    <encrypted>false</encrypted>\n")
	b.WriteString("    <auth>\n")
	fmt.Fprintf(&b, "      <username>%s</username>\n", xmlEsc(username))
	fmt.Fprintf(&b, "      <password>%s</password>\n", xmlEsc(password))
	b.WriteString("    </auth>\n")
	b.WriteString("    <join>\n")
	b.WriteString("      <channel>/</channel>\n")
	b.WriteString("      <password></password>\n")
	b.WriteString("    </join>\n")
	b.WriteString("  </host>\n")
	b.WriteString("</teamtalk>\n")
	return b.String()
}

// ttURL renders tt://user:pass@host:tcp:udp/ (urllib quote, safe="").
func ttURL(cfg Config, username, password string) string {
	return fmt.Sprintf("tt://%s:%s@%s:%d:%d/",
		pctEncode(username), pctEncode(password), cfg.PublicHost, cfg.TCPPort, cfg.UDPPort)
}

func xmlEsc(s string) string {
	r := strings.NewReplacer(
		"&", "&amp;",
		"<", "&lt;",
		">", "&gt;",
		`"`, "&quot;",
		"'", "&apos;",
	)
	return r.Replace(s)
}

// pctEncode percent-encodes every byte outside RFC3986 unreserved, matching
// urllib.parse.quote(s, safe="").
func pctEncode(s string) string {
	var b strings.Builder
	for i := 0; i < len(s); i++ {
		c := s[i]
		if isUnreserved(c) {
			b.WriteByte(c)
		} else {
			fmt.Fprintf(&b, "%%%02X", c)
		}
	}
	return b.String()
}

func isUnreserved(c byte) bool {
	return c >= 'A' && c <= 'Z' || c >= 'a' && c <= 'z' || c >= '0' && c <= '9' || c == '-' || c == '_' || c == '.' || c == '~'
}
