// Command ttcli exercises the text TeamTalk protocol via the Bot API against
// a live server. Usage:
//
//	ttcli -host H [-port 10333] -user BOT -pass PW \
//	    <status|channels|accounts|users|reg-test|pm|broadcast|chanmsg|setstatus|nick>
//
// Most actions print the resulting server state. It is meant as a protocol
// probe / smoke test, not as the production admin bot.
package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	tt "github.com/denizsincar29/teamtalk_reg_system/go/teamtalk"
)

func main() {
	log.SetFlags(0)
	log.SetOutput(os.Stdout)

	var (
		host, user, pass, nick, client, version string
		port                                    int
		pmUser, channelID, statusMode           int
		pmText, statusMsg, text, name           string
		regTest                                 bool
		noAutoSub                               bool
	)
	flag.StringVar(&host, "host", "", "TeamTalk server host")
	flag.IntVar(&port, "port", 10333, "TeamTalk TCP port")
	flag.StringVar(&user, "user", "", "bot account username")
	flag.StringVar(&pass, "pass", "", "bot account password")
	flag.StringVar(&nick, "nick", "ttgo", "bot nickname")
	flag.StringVar(&client, "client", "ttgo protocol probe", "client name")
	flag.StringVar(&version, "version", "5.14.0", "client version")
	flag.BoolVar(&regTest, "reg-test", false, "create a throwaway account and delete it")
	flag.IntVar(&pmUser, "pm-user", 0, "user id to send a private message to")
	flag.StringVar(&pmText, "pm-text", "", "private message text")
	flag.IntVar(&channelID, "channel", 0, "channel id for chanmsg/join")
	flag.StringVar(&text, "text", "", "text for broadcast/chanmsg")
	flag.IntVar(&statusMode, "status-mode", 0, "status mode 0=online 1=away 2=question")
	flag.StringVar(&statusMsg, "status-msg", "", "status message")
	flag.StringVar(&name, "nick-to", "", "new nickname")
	flag.BoolVar(&noAutoSub, "no-subscribe", false, "disable auto-subscribe")
	flag.Parse()

	action := flag.Arg(0)
	if host == "" || user == "" {
		log.Fatal("required: -host -user -pass and an action")
	}
	if action == "" {
		action = "status"
	}

	evs := make(chan tt.Event, 64)
	bot := tt.NewBot(tt.BotHandler{
		OnEvent: func(ev tt.Event) {
			select {
			case evs <- ev:
			default:
			}
		},
	})
	if err := bot.Connect(tt.BotConfig{
		Host: host, Port: port,
		Nickname: nick, Username: user, Password: pass,
		ClientName: client, Version: version,
		NoAutoSubscribe: noAutoSub,
		KeepAlive:       15 * time.Second,
	}); err != nil {
		log.Fatalf("connect/login: %v", err)
	}
	defer bot.Close()

	// Give the server a beat to push initial state (channels, users).
	time.Sleep(1200 * time.Millisecond)

	fmt.Printf("== logged in. selfID=%d selfChannel=%d channels=%d users=%d\n",
		bot.MyID(), bot.MyChannelID(), len(bot.Channels()), len(bot.Users()))

	switch action {
	case "status":
		fmt.Printf("channels: %d, users: %d\n", len(bot.Channels()), len(bot.Users()))
	case "channels":
		for _, c := range bot.Channels() {
			fmt.Printf("chan %d parent=%d type=%d maxusers=%d %q path=%s\n",
				c.ID, c.ParentID, c.Type, c.MaxUsers, c.Name, bot.ChannelPath(c.ID))
		}
	case "accounts":
		accs, err := bot.ListAccounts()
		die(err)
		for _, a := range accs {
			fmt.Printf("acct %-24s type=%d rights=%d note=%q\n", a.Username, a.UserType, a.UserRights, a.Note)
		}
	case "users":
		for _, u := range bot.Users() {
			fmt.Printf("user %-6d ch=%-5d mode=%d nick=%-20q uname=%q\n",
				u.ID, u.ChannelID, u.StatusMode, u.Nickname, u.Username)
		}
	case "reg-test":
		uname := fmt.Sprintf("gotest_%d", time.Now().Unix())
		upass := fmt.Sprintf("Gt#%d", time.Now().UnixNano())
		if err := bot.CreateAccount(uname, upass, tt.UserTypeDefault, 0, "ttcli probe"); err != nil {
			log.Fatalf("create account %q: %v", uname, err)
		}
		fmt.Printf("created %q ok\n", uname)
		exists, err := bot.AccountExists(uname)
		die(err)
		fmt.Printf("account exists: %v\n", exists)
		if err := bot.DeleteAccount(uname); err != nil {
			log.Fatalf("delete account: %v", err)
		}
		fmt.Printf("deleted %q ok\n", uname)
	case "pm":
		if pmUser == 0 || pmText == "" {
			log.Fatal("pm needs -pm-user and -pm-text")
		}
		if err := bot.SendToUser(pmUser, pmText); err != nil {
			log.Fatalf("pm: %v", err)
		}
		fmt.Printf("pm delivered to user %d\n", pmUser)
	case "broadcast":
		if text == "" {
			log.Fatal("broadcast needs -text")
		}
		if err := bot.SendBroadcast(text); err != nil {
			log.Fatalf("broadcast: %v", err)
		}
		fmt.Println("broadcast sent")
	case "chanmsg":
		if channelID == 0 || text == "" {
			log.Fatal("chanmsg needs -channel and -text")
		}
		if err := bot.SendToChannel(channelID, text); err != nil {
			log.Fatalf("chanmsg: %v", err)
		}
		fmt.Printf("channel message sent to %d\n", channelID)
	case "setstatus":
		if err := bot.ChangeStatus(statusMode, statusMsg); err != nil {
			log.Fatalf("setstatus: %v", err)
		}
		fmt.Printf("status set mode=%d msg=%q\n", statusMode, statusMsg)
	case "nick":
		if name == "" {
			log.Fatal("nick needs -nick-to")
		}
		if err := bot.ChangeNickname(name); err != nil {
			log.Fatalf("nick: %v", err)
		}
		fmt.Printf("nick changed to %q\n", name)
	case "join":
		if channelID == 0 {
			log.Fatal("join needs -channel")
		}
		drainEvents(evs)
		if err := bot.JoinChannel(channelID, ""); err != nil {
			log.Fatalf("join: %v", err)
		}
		time.Sleep(800 * time.Millisecond) // let the self-join push arrive
		fmt.Printf("joined %d; now in %d\n", channelID, bot.MyChannelID())
		fmt.Println("-- events after join:")
		waitEvents(evs, 100*time.Millisecond)
		fmt.Println("-- users:")
		for _, u := range bot.Users() {
			fmt.Printf("  user %d ch=%d nick=%q uname=%q\n", u.ID, u.ChannelID, u.Nickname, u.Username)
		}
	case "wait":
		fmt.Println("listening 10s for events...")
		waitEvents(evs, 10*time.Second)
	default:
		log.Fatalf("unknown action %q", action)
	}
}

func die(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

func drainEvents(evs <-chan tt.Event) {
	for {
		select {
		case <-evs:
		default:
			return
		}
	}
}

func waitEvents(evs <-chan tt.Event, d time.Duration) {
	t := time.NewTimer(d)
	defer t.Stop()
	for {
		select {
		case ev := <-evs:
			fmt.Printf("ev %s %s\n", evKind(ev.Kind), summarize(ev.Line))
		case <-t.C:
			return
		}
	}
}

func summarize(l tt.Line) string {
	parts := []string{l.Cmd}
	for k, v := range l.Vars {
		if k == tt.KeyPassword || k == tt.KeyOpPassword {
			continue
		}
		parts = append(parts, k+"="+v)
	}
	return strings.Join(parts, " ")
}

var kindNames = map[tt.EventKind]string{
	tt.EvUnknown: "unknown", tt.EvServerUpdate: "serverupdate",
	tt.EvChannelAdded: "channeladded", tt.EvChannelUpdated: "channelupdated",
	tt.EvChannelRemoved: "channelremoved", tt.EvUserJoined: "joined",
	tt.EvUserLeft: "left", tt.EvUserLoggedIn: "loggedin", tt.EvUserLoggedOut: "loggedout",
	tt.EvUserAdded: "useradded", tt.EvUserUpdated: "userupdated", tt.EvUserRemoved: "userremoved",
	tt.EvUserKicked: "kicked", tt.EvUserBanned: "banned", tt.EvMessage: "message",
	tt.EvAccountAdded: "accountadded", tt.EvAccountRemoved: "accountremoved", tt.EvPong: "pong",
}

func evKind(k tt.EventKind) string {
	if s, ok := kindNames[k]; ok {
		return s
	}
	return fmt.Sprintf("kind(%d)", int(k))
}
