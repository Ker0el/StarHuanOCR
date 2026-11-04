; 星幻OCR 安装包脚本
; 编译：ISCC.exe build\StarHuanOCR.iss   （Git Bash 下需 MSYS_NO_PATHCONV=1）

#define MyAppName "星幻OCR"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "星空"
#define MyAppURL "https://space.bilibili.com/177308205"
#define MyAppExeName "StarHuanOCR.exe"
#define BuildRoot ".."

[Setup]
AppId={{76EE9FC0-1A3B-4FAB-8BD9-89D10C7B5B0A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; 保留目录页并始终显示（不写 WizardSizePercent，保持默认 120）
DisableDirPage=no
AlwaysShowDirOnReadyPage=yes
OutputDir={#BuildRoot}\dist\installer
OutputBaseFilename=星幻OCR_Setup_v{#MyAppVersion}
SetupIconFile={#BuildRoot}\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern dynamic
; 绿色按用户安装：写 HKCU 自启、配置在 %APPDATA%，不需要管理员
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
InfoBeforeFile={#BuildRoot}\build\installer\install_info.txt
ShowLanguageDialog=no
LanguageDetectionMethod=uilanguage

[Languages]
Name: "chinese"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: checkedonce

[Files]
Source: "{#BuildRoot}\dist\StarHuanOCR\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[Code]
procedure CancelButtonClick(CurPageID: Integer; var Cancel, Confirm: Boolean);
begin
  { 安装开始前取消不弹确认；开始后保留确认，避免装一半 }
  if CurPageID < wpInstalling then
    Confirm := False;
end;
