#define AppName "2TTS"
#define AppVersion "1.0.8"
#define AppVersionInfo "1.0.8.0"
#define AppPublisher "2TTS"
#define AppExeName "2TTS.exe"

[Setup]
AppId={{D20A6E4D-70D7-4C48-A6A9-7E60F1B5B4A7}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern

SetupIconFile=..\resources\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}

VersionInfoVersion={#AppVersionInfo}
VersionInfoProductVersion={#AppVersionInfo}

CloseApplications=yes
RestartApplications=no

Compression=lzma2
SolidCompression=yes

OutputDir=..\dist_installer
OutputBaseFilename={#AppName}-Setup-{#AppVersion}

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\dist\2TTS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
