import sys, os, grp, pwd, time, re, argparse
import evdev
import traceback, logging, logging.handlers

def main():

    #
    # Set up logging to syslog and stderr
    #

    formatter = logging.Formatter('%(name)s[%(process)s]: %(message)s')
    log = logging.getLogger('oskbdaemon')
    log.setLevel(logging.DEBUG)
    syslog = logging.handlers.SysLogHandler(address = '/dev/log')
    syslog.setFormatter(formatter)
    log.addHandler(syslog)
    # Additionally log to stderr, for as long as that goes somewhere
    stderrlog = logging.StreamHandler(sys.stderr)
    stderrlog.setLevel(logging.DEBUG)
    stderrlog.setFormatter(formatter)
    log.addHandler(stderrlog)

    #
    # Parse arguments
    #

    ap = argparse.ArgumentParser()
    ap.add_argument('--user', '-u', help='user that can inject keystrokes', metavar='<user>', default='root')
    ap.add_argument('--group', '-g', help='group that can inject keystrokes', metavar='<group>')
    ap.add_argument('--keypipe', '-p', help='filename for keypipe', metavar='<filename>',
        default='/var/run/oskb-keypipe')
    ap.add_argument('--debug', help='logs every keystroke (UNSAFE!)', action='store_true')
    ap.add_argument('--nodaemon', help='stay in the foreground', action='store_true')
    cmdline = ap.parse_args()


    #
    # uid and gid for pipe file
    #
    
    try:
        pipeuid = pwd.getpwnam(cmdline.user).pw_uid
        if cmdline.group:
            pipegid = grp.getgrnam(cmdline.group).gr_gid
        else:
            pipegid = -1
    except:
        log.error('Error: user or group name not found, exiting.')
        sys.exit(-1)


    #
    # Create named pipe
    #

    try:
        os.umask(0o000)
        try:
            os.unlink(cmdline.keypipe)
        except:
            pass

        if cmdline.group:
            os.mkfifo(cmdline.keypipe, 0o660)
        else:
            os.mkfifo(cmdline.keypipe, 0o600)
        os.chown(cmdline.keypipe, pipeuid, pipegid)
        pipe = os.open(cmdline.keypipe, os.O_RDONLY | os.O_NONBLOCK)
    except PermissionError:
        log.error('Error: permission denied when creating keypipe. (Not root?)')
        sys.exit(-2)
    except:
        log.error('Error: Could not create named pipe for keyboard stream.')
        sys.exit(-3)


    #
    # Set up key injection
    #

    try:
        inject = evdev.UInput()
    except:
        log.error('Error: Could not set up keyboard injection, exiting.')
        sys.exit(-4)


    #
    # Drop privs
    #

    try:
        os.setgroups([])
        g = grp.getgrnam('nogroup').gr_gid
        os.setegid(g)
        u = pwd.getpwnam('nobody').pw_uid
        os.setuid(u)
    except:
        log.error('Error: Could not drop privs after setting up keyboard injection.')
        sys.exit(-5)


    # 
    # Daemonize
    #

    if not cmdline.nodaemon:
        pid = os.fork()             # Create first fork
        if pid > 0:
            sys.exit(0)
        os.setsid()                 # Decouple fork
        pid = os.fork()             # Create second fork
        if pid > 0:
            sys.exit(0)
        # redirect standard file descriptors to devnull
        infd = open(os.devnull, 'r')
        outfd = open(os.devnull, 'a+')
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(infd.fileno(), sys.stdin.fileno())
        os.dup2(outfd.fileno(), sys.stdout.fileno())
        os.dup2(outfd.fileno(), sys.stderr.fileno()) 


    #
    # Wait for keystrokes to come down pipe and inject them
    #

    try:
        log.info('Listening for keystrokes on %s', cmdline.keypipe)
        regexp = re.compile("(\d+) ([01])")
        while True:
            try:
                buf = os.read(pipe, 1024).decode('ascii')
            except OSError as e:
                if e.errno == 11:
                    time.sleep(0.1)
                    continue
            if buf:
                for line in buf.splitlines():
                    found = regexp.fullmatch(line)
                    if found:
                        keystroke = found.group(1)
                        updown = found.group(2)
                        action = 'pressed' if updown == '1' else 'released'
                        if cmdline.debug:
                            log.debug('key %s %s', keystroke, action)
                        inject.write(evdev.ecodes.EV_KEY, int(keystroke), int(updown))
                        inject.syn()
                    else:
                        log.warning('Received invalid keystroke data: %s', line) 
            time.sleep(0.001)
    except:
        try:
            inject.close()
            pipe.close()
        except:
            pass
        exc_type, exc_value, exc_traceback = sys.exc_info()
        log_msg = '\n'.join([''.join(traceback.format_tb(exc_traceback)), '{0}: {1}'.format(exc_type.__name__, exc_value)])
        log.error(repr(sys.exc_info()[1]))
        sys.exit(-6)
        

if __name__ == '__main__':
    main()