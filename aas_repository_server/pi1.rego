package policy

import future.keywords.if

default allow := false

allow if  
{
  input.path ==["get_identifiable"]
  input.method == "GET"
}

allow if  
{
  input.path ==["add_identifiable"]
  input.method == "POST"
}

