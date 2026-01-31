; MRA4 Dashboard Installer Script
; Erstellt mit Inno Setup

#define MyAppName "MRA4 Dashboard"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Ihr Firmenname"
#define MyAppExeName "MRA4_Dashboard.exe"
#define MyAppURL "https://www.example.com/"

[Setup]
; Grundlegende Installer-Informationen
AppId={{A1B2C3D4-E5F6-47A8-B9C0-D1E2F3A4B5C6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=Output
OutputBaseFilename=MRA4_Dashboard_Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Hauptanwendung und alle Dateien aus dem dist-Ordner
Source: "dist\MRA4_Dashboard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Config-Datei im AppData-Verzeichnis
Source: "..\config.json"; DestDir: "{userappdata}\MRA4_Dashboard"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Anwendung nach Installation starten (optional)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Prüfen ob .NET Framework installiert ist (falls benötigt)
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// Firewall-Regel hinzufügen (optional, für Modbus TCP)
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Firewall-Ausnahme für die Anwendung hinzufügen
    Exec('netsh', 'advfirewall firewall add rule name="MRA4 Dashboard" dir=in action=allow program="' + ExpandConstant('{app}\{#MyAppExeName}') + '" enable=yes', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Firewall-Regel entfernen
    Exec('netsh', 'advfirewall firewall delete rule name="MRA4 Dashboard"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
