& 'C:\Program Files\MySQL\MySQL Workbench 8.0\mysqldump.exe' -u root -pmaurof archivio_omelie_nuovo --result-file="C:\tmp\omelie_nuovo\backup_archivio.sql"


# e poi per salvarlo su github
#git add backup_archivio.sql
#git commit -m "Backup del database allo stato attuale"
#git push


# verifica
#git fetch origin
#git ls-tree -r origin/main --name-only

# git diff --name-only origin/main
# Per visualizzare esattamente cosa è cambiato all'interno dei file:
# git diff origin/main


# Esegui questi comandi per tracciarli, fare il commit e inviarli al repository remoto:
# git add .
# git commit -m "Aggiunti script PowerShell per backup DB e verifica trascrizioni"
# git push

# Se preferisci che questi script rimangano solo sul tuo computer locale, aggiungili al file .gitignore:
# Add-Content .gitignore "`nbackup_db.ps1`nverifica_trascrizioni.ps1"
# git add .gitignore
# git commit -m "Aggiornato .gitignore per ignorare gli script locali"
# git push