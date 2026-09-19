[Setup]
AppId={{C8E19B24-11FA-4A2B-8E9D-A492E9A7012D}
AppName=Kiri
AppVersion=4.0.0
AppPublisher=Reinhart
AppPublisherURL=https://reinhart.pages.dev
AppSupportURL=https://t.me/kiri0507
AppUpdatesURL=https://reinhart.pages.dev
DefaultDirName={autopf}\Kiri
DefaultGroupName=Kiri
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=Kiri_Setup_x64
SetupIconFile=images\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\Kiri.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "images\*"; DestDir: "{app}\images"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Kiri"; Filename: "{app}\Kiri.exe"
Name: "{autodesktop}\Kiri"; Filename: "{app}\Kiri.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Kiri.exe"; Description: "{cm:LaunchProgram,Kiri}"; Flags: nowait postinstall skipifsilent
