railway variables --set "PROTECTED_CONTENT_USERNAME=researcher"

railway variables --set "PROTECTED_CONTENT_PASSWORD_HASH=$2a$10$gz0QhAn4NUXSJFgEsEo3KOP.No6A8iryiiGQNNuI5acsQqdfNYQXm"

railway variables --set "PROTECTED_DATASETS=detectiveqa,booookscore"

railway up
