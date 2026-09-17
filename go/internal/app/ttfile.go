package app

import (
	"encoding/base64"
	"fmt"
	"net/url"
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

// ttURL is the documented tt:// address (BearWare, "tt Files and tt:// URLs
// for TeamTalk Servers"): every field is a query parameter, the ports among
// them —
//
//	tt://host?tcpport=10333&udpport=10333&encrypted=false&username=…&password=…
//
// The ports must NOT be written into the authority as "host:10333:10333": that
// is not a shape the scheme defines, and a phone rejects the whole address as
// invalid. Only this form goes to end users.
func ttURL(cfg Config, username, password string) string {
	return fmt.Sprintf("tt://%s?tcpport=%d&udpport=%d&encrypted=false&username=%s&password=%s",
		cfg.PublicHost, cfg.TCPPort, cfg.UDPPort,
		pctEncode(username), pctEncode(password))
}

// ttURLUserInfo is the older tt://user:pass@host:tcp:udp/ shape the Python
// system produced. The scheme does not document it, so it never leaves the
// landing page as the primary link — it stays as the second button for a
// desktop client that prefers the compact form.
func ttURLUserInfo(cfg Config, username, password string) string {
	return fmt.Sprintf("tt://%s:%s@%s:%d:%d/",
		pctEncode(username), pctEncode(password), cfg.PublicHost, cfg.TCPPort, cfg.UDPPort)
}

// ttShortURL renders the messenger-friendly link for one account: an https URL
// on ShortHost that /tturl turns back into the tt:// address. Chat clients only
// link https, so this is what actually gets pasted into a conversation; the
// password rides base64-encoded, exactly as in the public .tt download link.
func ttShortURL(cfg Config, username, password string) string {
	return fmt.Sprintf("https://%s/tturl?u=%s&p=%s",
		cfg.ShortHost,
		url.QueryEscape(username),
		base64.RawURLEncoding.EncodeToString([]byte(password)))
}

// ttOpenURL renders the landing page a push notification taps into. A phone
// refuses to open a bare tt:// address from a notification, and it also refuses
// the redirect /tturl answers with — Safari reports "cannot show URL" — so the
// tap lands on a page that navigates to the address itself.
func ttOpenURL(cfg Config, username, password string) string {
	return fmt.Sprintf("https://%s/open?u=%s&p=%s",
		cfg.ShortHost,
		url.QueryEscape(username),
		base64.RawURLEncoding.EncodeToString([]byte(password)))
}

// adminAccountURL is the admin dashboard opened on one account — the tap target
// of a "new registration" push, so the owner lands on the fresh account instead
// of the tt:// address the other notifications carry.
func adminAccountURL(cfg Config, username string) string {
	return fmt.Sprintf("https://%s/admin/?account=%s", cfg.ShortHost, url.QueryEscape(username))
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
