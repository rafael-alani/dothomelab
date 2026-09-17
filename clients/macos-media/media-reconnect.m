// Native NetAuth/Keychain mounting: no password is read or stored by this helper.
#import <Foundation/Foundation.h>
#import <NetFS/NetFS.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/file.h>
#include <sys/wait.h>
#include <dirent.h>
#include <signal.h>
#include <unistd.h>

static const char *mountPath = "/Volumes/Media";

static int musicProbe(void) {
    // A stale SMB filesystem must not hang the reconnect job indefinitely.
    pid_t child = fork();
    if (child < 0) return EAGAIN;
    if (child == 0) {
        alarm(5);
        DIR *dir = opendir("/Volumes/Media/music");
        if (!dir) _exit(errno > 0 && errno < 255 ? errno : EIO);
        errno = 0;
        struct dirent *entry;
        while ((entry = readdir(dir))) {
            if (strcmp(entry->d_name, ".") && strcmp(entry->d_name, "..")) {
                closedir(dir);
                _exit(0);
            }
        }
        int result = errno ? errno : ENOENT;
        closedir(dir);
        _exit(result);
    }
    for (int i = 0; i < 50; i++) {
        int status;
        if (waitpid(child, &status, WNOHANG) == child)
            return WIFEXITED(status) ? WEXITSTATUS(status) : ETIMEDOUT;
        usleep(100000);
    }
    kill(child, SIGKILL);
    waitpid(child, NULL, 0);
    return ETIMEDOUT;
}

static NSString *run(NSString *program, NSArray<NSString *> *args, int *status) {
    NSTask *task = [[NSTask alloc] init];
    task.executableURL = [NSURL fileURLWithPath:program];
    task.arguments = args;
    NSPipe *pipe = [NSPipe pipe];
    task.standardOutput = pipe;
    task.standardError = [NSFileHandle fileHandleWithNullDevice];
    NSError *error;
    if (![task launchAndReturnError:&error]) { *status = 1; return @""; }
    NSData *data = [pipe.fileHandleForReading readDataToEndOfFile];
    [task waitUntilExit];
    *status = task.terminationStatus;
    return [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding] ?: @"";
}

static int mounted(void) {
    struct statfs *mounts;
    int count = getmntinfo(&mounts, MNT_NOWAIT);
    if (count <= 0) return -1;
    for (int i = 0; i < count; i++) {
        NSString *source = @(mounts[i].f_mntfromname);
        BOOL ours = [source isEqualToString:@"//afa@192.168.0.110/Media"];
        BOOL here = !strcmp(mounts[i].f_mntonname, mountPath);
        if (here) return ours && !strcmp(mounts[i].f_fstypename, "smbfs") ? 1 : -1;
        // Do not create duplicate Media-1 mounts or silently change Kew's path.
        if (ours) return -1;
    }
    return 0;
}

int main(int argc, const char **argv) {
    @autoreleasepool {
        alarm(25);
        NSString *lockPath = [NSHomeDirectory() stringByAppendingPathComponent:
            @"Library/Application Support/dothomelab-media/reconnect.lock"];
        int lock = open(lockPath.fileSystemRepresentation, O_CREAT | O_RDWR | O_NOFOLLOW, 0600);
        if (lock < 0 || flock(lock, LOCK_EX)) return 1;
        int state = mounted();
        if (state < 0) { fprintf(stderr, "Media mount/path conflict; leaving it unchanged.\n"); return 1; }
        if (argc == 2 && !strcmp(argv[1], "--check"))
            return state == 1 && musicProbe() == 0 ? 0 : 1;
        if (argc != 1) return 2;
        if (state == 1 && musicProbe() == 0) return 0;

        int status;
        run(@"/usr/bin/nc", @[@"-G", @"2", @"-z", @"192.168.0.110", @"445"], &status);
        if (status) return 1; // Offline: quiet retry on the next launchd interval.
        NSString *arp = run(@"/usr/sbin/arp", @[@"-n", @"192.168.0.110"], &status);
        // Scope reconnects to the declared Infra LAN NIC, not another Wi-Fi's
        // device using the same private IP. This is a LAN guard, not cryptographic identity.
        if (status || ![[arp lowercaseString] containsString:@" at bc:24:11:eb:87:25 on "]) return 1;

        if (state == 1) {
            int result = musicProbe();
            if (!result) return 0;
            if (result != ETIMEDOUT && result != EIO && result != ENOTCONN && result != ESTALE)
                return 1;
            // Never force-detach an in-use filesystem. Let SMB recover busy mounts.
            run(@"/usr/sbin/diskutil", @[@"unmount", @"/Volumes/Media"], &status);
            if (status || mounted() != 0) return 1;
        }
        // Refuse ordinary files/directories rather than deleting an obstruction.
        struct stat info;
        if (lstat(mountPath, &info) == 0) {
            fprintf(stderr, "Unmounted /Volumes/Media exists; leaving it unchanged.\n");
            return 1;
        }
        if (errno != ENOENT) return 1;
        NSMutableDictionary *openOptions = [@{(__bridge NSString *)kNAUIOptionKey:
            (__bridge NSString *)kNAUIOptionNoUI} mutableCopy];
        NSMutableDictionary *mountOptions = [@{(__bridge NSString *)kNetFSMountFlagsKey:
            @(MNT_RDONLY)} mutableCopy];
        CFArrayRef points = NULL;
        int result = NetFSMountURLSync((__bridge CFURLRef)[NSURL URLWithString:@"smb://afa@192.168.0.110/Media"],
            NULL, NULL, NULL, (__bridge CFMutableDictionaryRef)openOptions,
            (__bridge CFMutableDictionaryRef)mountOptions, &points);
        if (points) CFRelease(points);
        if (result) { fprintf(stderr, "Media reconnect failed (NetFS %d).\n", result); return 1; }
        if (mounted() != 1 || musicProbe()) return 1;
        puts("Media reconnected at /Volumes/Media; music is readable.");
        return 0;
    }
}
