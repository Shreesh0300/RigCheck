import React, { useState } from 'react';

export default function LandingPage({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    // Simulate login success instantly
    onLogin();
  };

  return (
    <div 
      className="relative min-h-screen w-full flex items-center justify-center bg-black overflow-hidden font-['Inter',ui-sans-serif,system-ui,sans-serif]"
    >
      {/* Background Image Layer */}
      <div 
        className="absolute inset-0 z-0 bg-center bg-no-repeat bg-black"
        style={{ backgroundImage: "url('/sign-in.jpg')", backgroundSize: "100% 100%", filter: "brightness(0.85) contrast(1.1)" }}
      ></div>

      {/* Glassmorphism Panel */}
      <div className="relative z-10 w-full max-w-md mx-auto p-8 rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur-xl shadow-[0_0_50px_rgba(0,0,0,0.5)] flex flex-col items-center">
        
        {/* Logo and Branding */}
        <div className="flex items-center space-x-3 mb-2">
          {/* Controller Icon SVG */}
          <div className="text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]">
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="6" width="20" height="12" rx="5" ry="5"></rect>
              <line x1="6" y1="12" x2="10" y2="12"></line>
              <line x1="8" y1="10" x2="8" y2="14"></line>
              <line x1="15" y1="13" x2="15.01" y2="13"></line>
              <line x1="18" y1="11" x2="18.01" y2="11"></line>
            </svg>
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-white drop-shadow-md">
            Rig<span className="text-cyan-400">Check</span>
          </h1>
        </div>
        <p className="text-slate-300 font-medium mb-8 text-lg">Login to Discover your next game</p>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="w-full flex flex-col space-y-5">
          <div className="flex flex-col space-y-1">
            <label className="text-sm font-medium text-slate-300 ml-1">Email Address</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>
              </div>
              <input 
                type="email" 
                placeholder="Enter your email address"
                className="w-full pl-10 pr-4 py-3 bg-slate-900/50 border border-slate-700/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-400 transition-colors"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          <div className="flex flex-col space-y-1">
            <div className="flex justify-between items-center ml-1">
              <label className="text-sm font-medium text-slate-300">Password</label>
              <a href="#" className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors">Forgot Password?</a>
            </div>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
              </div>
              <input 
                type="password" 
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-3 bg-slate-900/50 border border-slate-700/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-400 transition-colors"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <button 
            type="submit"
            className="w-full py-3 mt-4 bg-cyan-400 hover:bg-cyan-300 text-slate-900 font-bold rounded-lg shadow-[0_0_15px_rgba(34,211,238,0.4)] hover:shadow-[0_0_25px_rgba(34,211,238,0.6)] transition-all flex items-center justify-center space-x-2"
          >
            <span>Sign In</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
          </button>
        </form>

        <div className="w-full flex items-center my-6">
          <div className="flex-grow border-t border-slate-700/50"></div>
          <span className="px-3 text-xs text-slate-400 uppercase tracking-widest">Or continue with</span>
          <div className="flex-grow border-t border-slate-700/50"></div>
        </div>

        {/* Social Logins */}
        <div className="w-full grid grid-cols-2 gap-3">
          <button className="flex items-center justify-center space-x-2 bg-slate-800/80 hover:bg-slate-700 border border-slate-700/50 py-2.5 rounded-lg text-sm font-medium text-white transition-colors">
            {/* Steam Icon minimal SVG */}
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M11.967 0C5.356 0 0 5.359 0 11.97c0 4.606 2.592 8.618 6.402 10.597L9.42 16.27a4.912 4.912 0 0 1-1.397-2.144L3.6 12.822a.566.566 0 0 1-.362-.68c.245-.98 1.573-4.669 5.867-5.614 3.037-.67 6.13.257 8.356 2.457 2.222 2.196 2.923 5.358 1.83 8.363l3.666 4.708c2.977-2.274 4.88-5.83 4.88-9.832 0-6.61-5.356-11.968-11.967-11.968zm5.725 15.655a3.195 3.195 0 0 1-4.043.682l-2.455 3.486a4.856 4.856 0 0 0 4.904 1.487c2.261-.502 3.864-2.528 3.822-4.838l-2.228-1.573zM10.15 13.9a1.7 1.7 0 1 0 0-3.4 1.7 1.7 0 0 0 0 3.4z"/>
            </svg>
            <span>Steam</span>
          </button>
          
          <button className="flex items-center justify-center space-x-2 bg-slate-800/80 hover:bg-slate-700 border border-slate-700/50 py-2.5 rounded-lg text-sm font-medium text-white transition-colors">
            {/* Google Icon minimal SVG */}
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            <span>Google</span>
          </button>
        </div>

        {/* Footer Links */}
        <div className="w-full flex justify-between mt-8 text-xs text-slate-400">
          <a href="#" className="hover:text-cyan-400 transition-colors">Create an Account</a>
          <div className="space-x-3">
            <a href="#" className="hover:text-white transition-colors">Terms of Service</a>
            <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
          </div>
        </div>

      </div>
    </div>
  );
}
