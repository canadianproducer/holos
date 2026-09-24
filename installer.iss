; Inno Setup 6: інсталятор Holos-Setup.exe (без прав адміністратора)
#ifndef Variant
  #define Variant "cpu"
#endif
#define AppName "Голос"
#define AppVersion "0.2.0"

[Setup]
AppId={{6C1E2B7A-4F4B-4E8B-9C2A-5A1D0C0F0001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Canadian Producer
DefaultDirName={localappdata}\Programs\Holos
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=Holos-Setup-{#Variant}
SetupIconFile=assets\holos.ico
UninstallDisplayIcon={app}\Holos.exe
Compression=lzma2/fast
SolidCompression=no
DiskSpanning=no
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "uk"; MessagesFile: "compiler:Languages\Ukrainian.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Ярлик на робочому столі"; Flags: unchecked
Name: "autostart"; Description: "Запускати разом з Windows"

[Files]
Source: "dist\Holos\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\Holos.exe"
Name: "{group}\Видалити {#AppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\Holos.exe"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\Holos.exe"; Tasks: autostart

[Run]
Filename: "{app}\Holos.exe"; Description: "Запустити {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/IM Holos.exe /F"; Flags: runhidden; RunOnceId: "KillHolos"
