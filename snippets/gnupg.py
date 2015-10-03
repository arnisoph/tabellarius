python:

#batch = gpg.gen_key_input(key_type="RSA", key_length=4096, name_real='Tabellarius GPG Key for Arnold Bechtoldt', name_email='mail@arnoldbechtoldt.com', passphrase='w00t', expire_date='5y')
#key = gpg.gen_key(batch)
#out = gpg.encrypt('<PASSWORD>', '7FEC1FAD', cipher_algo='AES256', digest_algo='SHA512')

cli:
# tr -d '\n' < pwd_plain.tmp | gpg2 --armor --recipient 4BBFD7E2 --encrypt #TODO algo?
