```text
         .8.          8 8888         8 8888  `8.`8888.      ,8'       ,o888888o.    8888 8888
        .888.         8 8888         8 8888   `8.`8888.    ,8'       8888     `88.   88   88 
       :88888.        8 8888         8 8888    `8.`8888.  ,8'     ,8 8888       `8.  88   88
      . `88888.       8 8888         8 8888     `8.`8888.,8'      88 8888            88   88
     .8. `88888.      8 8888         8 8888      `8.`88888'       88 8888            88   88
    .8`8. `88888.     8 8888         8 8888       `8. 8888        88 8888            88   88
   .8' `8. `88888.    8 8888         8 8888        `8 8888        88 8888            88   88
  .8'   `8. `88888.   8 8888         8 8888         8 8888        `8 8888       .8'  88   88
 .888888888. `88888.  8 8888         8 8888         8 8888           8888     ,88'   88   88
.8'       `8. `88888. 8 888888888888 8 888888888888 8 8888            `8888888P'    8888 8888

```

ally-c2 is an open source closs platform c2 framework
that is made to be light weight and customizable

## structure
in ally we have a separate server and cli based client
that connects to the server via ws/wss,
so you che host the server where you want

ally support multi operator mode
so you can work with a team the authentication
credentials are in **server/users.json** 

## installation

```
git clone https://github.com/piadi-su/ally-c2.git

# server
cd server
go build -o ally-server srv.go
./ally-server

# cli-client
cd cliclient
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 ally_cli.py

```

## users.json config
you need to set up **users.json**
before u login with cliclient,
the default credentials are
user=**ally**
passwd=**admin**

make sure to change them

#### get sha256 hash for users.json
```bash
echo -n "password" | sha256sum
```
