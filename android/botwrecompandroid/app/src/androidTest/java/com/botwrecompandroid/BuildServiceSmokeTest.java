package com.botwrecompandroid;

import android.app.Activity;
import android.app.ActivityManager;
import android.app.Instrumentation;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.os.SystemClock;

/** Device regression for a build that fails immediately, before its foreground service has started. */
public class BuildServiceSmokeTest extends Instrumentation {
    @Override public void onCreate(Bundle args) {
        super.onCreate(args);
        start();
    }

    private boolean foreground(Context context) {
        ActivityManager manager = context.getSystemService(ActivityManager.class);
        for (ActivityManager.RunningServiceInfo service : manager.getRunningServices(100))
            if (service.service.getClassName().equals(BuildService.class.getName())) return service.foreground;
        return false;
    }

    @Override public void onStart() {
        Bundle result = new Bundle();
        try {
            Context context = getTargetContext();
            Intent launch = context.getPackageManager().getLaunchIntentForPackage(context.getPackageName());
            launch.putExtra("env", "LARECOMP_NO_WRITE_TRACKING=1");
            context.startActivity(launch);
            SystemClock.sleep(4000);
            for (int i = 0; i < 10; i++) {
                BuildService.start(context);
                BuildService.progress(context, i);
                BuildService.stop(context);
            }
            SystemClock.sleep(8000); // Exceeds the normal foreground startup deadline.
            if (foreground(context)) throw new AssertionError("Service survived its stop command");
            BuildService.start(context);
            long deadline = SystemClock.uptimeMillis() + 5000;
            while (!foreground(context) && SystemClock.uptimeMillis() < deadline) SystemClock.sleep(50);
            if (!foreground(context)) throw new AssertionError("Service never entered the foreground");
            BuildService.progress(context, 50);
            BuildService.stop(context);
            deadline = SystemClock.uptimeMillis() + 5000;
            while (foreground(context) && SystemClock.uptimeMillis() < deadline) SystemClock.sleep(50);
            if (foreground(context)) throw new AssertionError("Service did not stop");
            result.putString("stream", "PASS: 10 immediate start/stop cycles, foreground promotion and normal stop\n");
            finish(Activity.RESULT_OK, result);
        } catch (Throwable error) {
            result.putString("stream", "FAIL: " + error + "\n");
            finish(Activity.RESULT_CANCELED, result);
        }
    }
}
