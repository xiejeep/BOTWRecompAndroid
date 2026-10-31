package com.botwrecompandroid;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.util.Log;

// While the game code builds (runtime/gamebuild.c, from the start screen's setup): a foreground service with the build's
// progress in a notification, and a partial wake lock. The build runs in the app's own process; without this Android
// stopped it when the screen went off or another app came to the front (a Galaxy S21 on Reddit: started over, "do it in
// the background"). It only keeps the process in the foreground and the CPU awake - the build itself is unchanged.
public class BuildService extends Service {
    private static final String TAG = "BOTWRecompAndroid";
    private static final String CHANNEL = "build";
    private static final int ID = 1;
    private static PowerManager.WakeLock wake;
    private static int shown = -1;
    private static final String STOP = "com.botwrecompandroid.STOP_BUILD";
    private static final Handler main = new Handler(Looper.getMainLooper());
    private static boolean requested;
    private static BuildService running;

    static void start(Context c) {
        Context app = c.getApplicationContext();
        main.post(() -> startOnMain(app));
    }

    private static void startOnMain(Context c) {
        requested = true;
        shown = -1;
        try {
            c.startForegroundService(new Intent(c, BuildService.class));
        } catch (Exception e) {  // (from the background Android may refuse: the build goes on without it)
            Log.w(TAG, "build service: " + e);
        }
    }

    static void stop(Context c) {
        Context app = c.getApplicationContext();
        main.post(() -> {
            requested = false;
            shown = -1;
            // Deliver the stop after the start command: stopService can cancel a pending foreground start
            // before onStartCommand has had a chance to call startForeground, causing an Android timeout.
            try {
                app.startService(new Intent(app, BuildService.class).setAction(STOP));
            } catch (Exception e) {
                Log.w(TAG, "build service: stop: " + e);
            }
        });
    }

    static void progress(Context c, int percent) {
        main.post(() -> {
            if (!requested || percent == shown) return;
            shown = percent;
            if (running != null) {
                NotificationManager nm = running.getSystemService(NotificationManager.class);
                if (nm != null) nm.notify(ID, notification(running, percent));
            }
        });
    }

    private static Notification notification(Context c, int percent) {
        Intent open = c.getPackageManager().getLaunchIntentForPackage(c.getPackageName());
        PendingIntent pi = open == null ? null : PendingIntent.getActivity(c, 0, open, PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(c, CHANNEL)
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle(c.getString(R.string.build_title))
                .setContentText(c.getString(R.string.build_text))
                .setProgress(100, Math.max(percent, 0), percent < 0)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setContentIntent(pi)
                .build();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (nm != null)
            nm.createNotificationChannel(new NotificationChannel(CHANNEL, getString(R.string.build_channel),
                    NotificationManager.IMPORTANCE_LOW));
        Notification n = notification(this, shown);
        try {
            if (Build.VERSION.SDK_INT >= 29) startForeground(ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
            else startForeground(ID, n);
        } catch (Exception e) {
            Log.w(TAG, "build service: not in the foreground: " + e);
            stopSelf(startId);
            return START_NOT_STICKY;
        }
        running = this;
        if (intent != null && STOP.equals(intent.getAction())) {
            stopSelf(startId);
            return START_NOT_STICKY;
        }
        if (wake == null) {
            PowerManager pm = getSystemService(PowerManager.class);
            if (pm != null) wake = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "botwrecomp:build");
        }
        if (wake != null && !wake.isHeld()) wake.acquire(4 * 60 * 60 * 1000L);  // (a stuck build lets go after 4 h)
        Log.i(TAG, "build service: on (the build goes on with the screen off)");
        return START_NOT_STICKY;
    }

    @Override
    public void onDestroy() {
        if (running == this) running = null;
        if (wake != null && wake.isHeld()) wake.release();
        Log.i(TAG, "build service: off");
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
