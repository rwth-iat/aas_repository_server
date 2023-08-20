package policy

import future.keywords.if
import future.keywords.in

default allow := false

allow if {
    user_is_admin
    path_is_get_id
    action_is_read
    some idKey
	input.resource == data.object_attributes[idKey]
}

allow if {
    user_is_student
    path_is_get_id
    action_is_read
    input.ressource == data.object_attributes.id2
}

allow if {
    user_is_admin
    path_is_add_id
    action_is_write
}

allow if {
    user_is_admin
    path_is_mod_id
    action_is_modify
}

allow if {
    user_is_admin
    path_is_query_sem_id
    action_is_read
    some idKey
	input.resource == data.object_attributes[idKey]
}

allow if {
    user_is_student
    path_is_query_sem_id
    action_is_read
    input.ressource == data.object_attributes.id2
}

user_is_admin if data.user_attributes[input.user].role=="admin"
user_is_student if data.user_attributes[input.user].role=="rwthStudent"
user_is_other if data.user_attributes[input.user].role=="otherStudent"

path_is_get_id if input.path==["get_identifiable"]
path_is_add_id if input.path==["add_identifiable"]
path_is_mod_id if input.path==["modify_identifiable"]
path_is_query_sem_id if input.path==["query_semantic_id"]

action_is_read if input.method=="GET"
action_is_write if input.method=="POST"
action_is_modify if input.method=="PUT"


