from pathlib import Path
import shutil
b=Path(__file__).resolve().parent
base=b.parent.parent
shutil.copy2(b/'shell.qml',base/'shell.qml')
shutil.copy2(b/'bar/Bar.qml',base/'bar/Bar.qml')
print('Restored. Press Super+Ctrl+R to restart Impasto.')
