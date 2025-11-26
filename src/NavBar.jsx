import React from "react";
import googlePic from "./images/google-pic.png";

function NavBar() {
  return (
    <>
      <nav class="navbar" role="navigation" aria-label="main navigation">
        <div id="navbarBasicExample" class="navbar-menu">
          <div class="navbar-start">
            <a
              href="https://about.google/?fg=1&utm_source=google-US&utm_medium=referral&utm_campaign=hp-header"
              class="navbar-item"
            >
              About
            </a>
            <div />
            <div class="navbar-start">
              <a
                href="https://store.google.com/us/?utm_source=hp_header&utm_medium=google_ooo&utm_campaign=GS100042&hl=en-US"
                class="navbar-item"
              >
                Store
              </a>
            </div>
            <div />
          </div>
          <div class="navbar-end">
          <a
            href="https://mail.google.com/mail/u/0/#inbox"
            class="navbar-item"
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
