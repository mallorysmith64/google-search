import React from "react";
import googlePic from "./images/google-pic.png";

function NavBar() {
  return (
    <>
      <nav className="navbar" role="navigation" aria-label="main navigation">
        <div id="navbarBasicExample" className="navbar-menu">
          <div className="navbar-start">
            <a
              href="https://about.google/?fg=1&utm_source=google-US&utm_medium=referral&utm_campaign=hp-header"
              className="navbar-item"
            >
              About
            </a>
            <div />
            <div className="navbar-start">
              <a
                href="https://store.google.com/us/?utm_source=hp_header&utm_medium=google_ooo&utm_campaign=GS100042&hl=en-US"
                className="navbar-item"
              >
                Store
              </a>
            </div>
            <div />
          </div>
          <div className="navbar-end">
          <a
            href="https://mail.google.com/mail/u/0/#inbox"
            className="navbar-item"
          >
            Gmail
          </a>
        </div>
        </div>
        
      </nav>
    </>
  );
}

export default NavBar;
