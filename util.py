def contains_none(args):
    return None in args


def assert_not_none(*args):
    if contains_none(args):
        raise ValueError("None arguments are not allowed in this function call.")


def get_student_testing_header():
    return {"Content-Type": "application/json",
            "oidc_claim_easy_role": "student",
            "oidc_claim_email": "foo@bar.com",
            "oidc_claim_given_name": "Foo",
            "oidc_claim_family_name": "Bar",
            "oidc_claim_preferred_username": "fp"}
