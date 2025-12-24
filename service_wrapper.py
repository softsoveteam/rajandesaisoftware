"""
Windows Service Wrapper for Signage Player
This allows the player to run as a Windows service that auto-starts on boot
"""
import sys
import os
import time
import subprocess
import win32serviceutil
import win32service
import servicemanager
import socket

class SignagePlayerService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SignagePlayer"
    _svc_display_name_ = "Signage Player Service"
    _svc_description_ = "Automatically plays scheduled videos on digital signage displays"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32serviceutil.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_alive = True
        
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.is_alive = False
        self.stop_event.set()
        
    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()
        
    def main(self):
        # Get the directory where the service executable is located
        if getattr(sys, 'frozen', False):
            # Running as compiled EXE
            exe_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        
        player_exe = os.path.join(exe_dir, "SignagePlayer.exe")
        
        if not os.path.exists(player_exe):
            servicemanager.LogErrorMsg(f"SignagePlayer.exe not found at: {player_exe}")
            return
        
        servicemanager.LogInfoMsg(f"Starting Signage Player from: {player_exe}")
        
        # Start the player process
        process = None
        restart_count = 0
        max_restarts = 10  # Prevent infinite restart loops
        
        while self.is_alive:
            try:
                if process is None or process.poll() is not None:
                    # Process not running or has exited
                    if process and process.poll() is not None:
                        exit_code = process.poll()
                        servicemanager.LogWarningMsg(
                            f"Signage Player exited with code {exit_code}. Restarting..."
                        )
                        restart_count += 1
                        
                        if restart_count > max_restarts:
                            servicemanager.LogErrorMsg(
                                f"Signage Player crashed {max_restarts} times. Stopping service."
                            )
                            break
                        
                        # Wait a bit before restarting
                        time.sleep(5)
                    
                    # Start the player
                    servicemanager.LogInfoMsg("Starting Signage Player...")
                    process = subprocess.Popen(
                        [player_exe],
                        cwd=exe_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                    restart_count = 0  # Reset restart count on successful start
                
                # Check if service should stop
                if win32serviceutil.WaitForSingleObject(self.stop_event, 5000) == 0:
                    break
                    
            except Exception as e:
                servicemanager.LogErrorMsg(f"Error in service: {e}")
                time.sleep(10)
        
        # Stop the player process
        if process:
            try:
                process.terminate()
                process.wait(timeout=10)
            except:
                process.kill()
        
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPED,
            (self._svc_name_, '')
        )


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SignagePlayerService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SignagePlayerService)

