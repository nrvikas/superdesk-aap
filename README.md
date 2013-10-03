Superdesk REST API Server
=========================

Superdesk REST API Server is python app on top of mongodb.

## Dependencies

Application requires mongodb running on standard port.
Python version supported are 2.7.5+ and 3.3+.
Using virtualenv is recommended for installing python dependencies.

## Instalation

```sh
$ pip install -r requirements.txt
```

## Testing

```sh
$ behave
```

## Running Dev Server

```sh
$ python app.py
```

## Running cli commands

```sh
$ python manage.py
```

### Creating admin user

This command will create an administrator user.

```sh
$ python manage.py users:create -u <username> -p <password>
```

