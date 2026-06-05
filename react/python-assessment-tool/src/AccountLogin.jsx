import { useRef, useState, useEffect } from "react";
import Authentication from "./components/Authentication";
import { useNavigate, Link } from "react-router";

export default function AccountLogin({
  updateLoginSession,
  getSessionUsername,
  getSessionUserId,
}) {
  const registrationLink = useRef();
  const [loginFailed, setLoginFailed] = useState(false); // Used when login fails (wrong password, etc.)
  let navigate = useNavigate();

  useEffect(() => {
    // Upon mount, if the user has already logged in, redirect to index.
    const USER_NAME = getSessionUsername();
    const USER_ID = getSessionUserId();
    if (
      USER_NAME !== "" &&
      USER_ID !== "" &&
      USER_NAME !== undefined &&
      USER_ID !== undefined &&
      USER_NAME !== null &&
      USER_ID !== null
    )
      navigate("/");
  }, []);

  const submitAction = (username, password) => {
    setLoginFailed(false);

    // Submit the login data
    const submission = {};
    submission["username"] = username;
    submission["password"] = password;

    const requestOptions = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(submission),
      credentials: 'include'
    };

    fetch(import.meta.env.VITE_FLASK_LOGIN, requestOptions).then((response) => {
      console.log(response.status);
      if (response.status == 200) {
        // Successful login
        response.text().then((text) => {
          // Remove the link to the REGISTRATION page
          registrationLink.current.remove();

          // The USER_ID is 2 indices away from ':'
          const USER_ID = text.slice(text.indexOf(": ") + 2);
          updateLoginSession(username, USER_ID);
          navigate("/");
        });
      } else {
        // Wrong password, etc.
        setLoginFailed(true);
      }
    });
  };

  return (
    <div>
      <Authentication
        purposeOfAuthentication="login"
        submitAction={submitAction}
        loginFailed={loginFailed}
      />
      <Link to="/register" ref={registrationLink}>
        Register
      </Link>
    </div>
  );
}
