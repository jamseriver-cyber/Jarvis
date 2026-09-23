#define AppVersion "0.2.0"

[Setup]
AppId={{F586D932-9DD1-41FD-B3F4-7B4AAF8A7228}
AppName=Personal Jarvis
AppVersion={#AppVersion}
AppPublisher=jamseriver-cyber
AppPublisherURL=https://github.com/jamseriver-cyber/Jarvis
DefaultDirName={localappdata}\Programs\Personal Jarvis
DefaultGroupName=Personal Jarvis
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
MinVersion=10.0
OutputDir=..\dist\installer
OutputBaseFilename=PersonalJarvis-Setup-{#AppVersion}-win64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\Jarvis.exe
LicenseFile=..\LICENSE
InfoBeforeFile=INSTALLER_NOTES.txt

[Files]
Source: "..\dist\Jarvis\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Personal Jarvis"; Filename: "{app}\Jarvis.exe"
Name: "{autodesktop}\Personal Jarvis"; Filename: "{app}\Jarvis.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: unchecked

[Run]
Filename: "{app}\Jarvis.exe"; Description: "启动 Jarvis 并完成首次设置"; Flags: postinstall nowait skipifsilent unchecked
