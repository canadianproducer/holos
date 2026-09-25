; Inno Setup 6: інсталятор Holos-Setup.exe (без прав адміністратора)
#ifndef Variant
  #define Variant "cpu"
#endif
#ifndef DistDir
  #define DistDir "dist\Holos"
#endif
#if Variant == "cpu"
  #define Suffix ""
#else
  #define Suffix "-" + Variant
#endif
#define AppName "Голос"
#define AppVersion "0.3.0"

[Setup]
AppId={{6C1E2B7A-4F4B-4E8B-9C2A-5A1D0C0F0001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Canadian Producer
DefaultDirName={localappdata}\Programs\Holos
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=Holos-Setup-{#AppVersion}{#Suffix}
SetupIconFile=assets\holos.ico
UninstallDisplayIcon={app}\Holos.exe
Compression=lzma2/fast
SolidCompression=no
DiskSpanning=no
WizardStyle=modern
CloseApplications=force
RestartApplications=no
AppPublisherURL=https://github.com/canadianproducer/holos
AppUpdatesURL=https://github.com/canadianproducer/holos/releases
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "uk"; MessagesFile: "compiler:Languages\Ukrainian.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Ярлик на робочому столі"; Flags: unchecked
Name: "autostart"; Description: "Запускати разом з Windows"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\Holos.exe"
Name: "{group}\Видалити {#AppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\Holos.exe"; Tasks: desktopicon

[InstallDelete]
; старий автозапуск (до 0.3.1) — через нього при старті Windows вискакувала помилка Holos.vbs
Type: files; Name: "{userstartup}\Holos.vbs"
Type: files; Name: "{userstartup}\{#AppName}.lnk"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Holos"; ValueData: """{app}\Holos.exe"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\Holos.exe"; Description: "Запустити {#AppName}"; Flags: nowait postinstall skipifsilent
; після тихого оновлення з програми — запускаємо нову версію
Filename: "{app}\Holos.exe"; Flags: nowait; Check: WizardSilent

[UninstallDelete]
Type: files; Name: "{userstartup}\Holos.vbs"

[UninstallRun]
Filename: "taskkill"; Parameters: "/IM Holos.exe /F"; Flags: runhidden; RunOnceId: "KillHolos"
