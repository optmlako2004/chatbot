/* Voyage Assistant — lucide-style icons (outline, 1.5 stroke).
   All icons take {size, className, strokeWidth} props.
   Exposed on window so other Babel scripts can use them. */

const VAIcon = ({ children, size = 20, strokeWidth = 1.5, className = '', style }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={strokeWidth}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    style={style}
  >
    {children}
  </svg>
);

/* Mode icons — distinct geometric shapes, same line weight */
const IPlane = (p) => (
  <VAIcon {...p}>
    <path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z" />
  </VAIcon>
);
const ITrain = (p) => (
  <VAIcon {...p}>
    <rect x="4" y="3" width="16" height="16" rx="2" />
    <path d="M4 11h16" />
    <path d="M12 3v8" />
    <path d="m8 19-2 3" />
    <path d="m18 22-2-3" />
    <circle cx="8" cy="15" r="0.8" fill="currentColor" />
    <circle cx="16" cy="15" r="0.8" fill="currentColor" />
  </VAIcon>
);
const IShip = (p) => (
  <VAIcon {...p}>
    <path d="M2 21c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2c1.3 0 1.9.5 2.5 1" />
    <path d="M19.4 16.5 22 11H2l2.6 5.5" />
    <path d="M12 11V2L5 5v6" />
    <path d="M12 2v9" />
    <path d="m6 11 1 8" />
    <path d="m18 11-1 8" />
  </VAIcon>
);
const IBus = (p) => (
  <VAIcon {...p}>
    <path d="M8 6v6" />
    <path d="M16 6v6" />
    <path d="M2 12h19.6" />
    <path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4 0-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H4a2 2 0 0 0-2 2v10h3" />
    <circle cx="7" cy="18" r="2" />
    <path d="M9 18h5" />
    <circle cx="16" cy="18" r="2" />
  </VAIcon>
);

/* Search / form */
const ISearch = (p) => (
  <VAIcon {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.5-3.5" />
  </VAIcon>
);
const IMapPin = (p) => (
  <VAIcon {...p}>
    <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0" />
    <circle cx="12" cy="10" r="2.5" />
  </VAIcon>
);
const ICalendar = (p) => (
  <VAIcon {...p}>
    <rect x="3" y="5" width="18" height="16" rx="2" />
    <path d="M3 10h18" />
    <path d="M8 3v4" />
    <path d="M16 3v4" />
  </VAIcon>
);
const IUsers = (p) => (
  <VAIcon {...p}>
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </VAIcon>
);
const ISwap = (p) => (
  <VAIcon {...p}>
    <path d="M7 16V4" />
    <path d="m3 8 4-4 4 4" />
    <path d="M17 8v12" />
    <path d="m21 16-4 4-4-4" />
  </VAIcon>
);

/* Arrows */
const IArrowRight = (p) => (
  <VAIcon {...p}>
    <path d="M5 12h14" />
    <path d="m13 5 7 7-7 7" />
  </VAIcon>
);
const IArrowLeft = (p) => (
  <VAIcon {...p}>
    <path d="M19 12H5" />
    <path d="m11 19-7-7 7-7" />
  </VAIcon>
);
const IArrowUp = (p) => (
  <VAIcon {...p}>
    <path d="M12 19V5" />
    <path d="m5 12 7-7 7 7" />
  </VAIcon>
);
const IChevronRight = (p) => (
  <VAIcon {...p}>
    <path d="m9 6 6 6-6 6" />
  </VAIcon>
);
const IChevronDown = (p) => (
  <VAIcon {...p}>
    <path d="m6 9 6 6 6-6" />
  </VAIcon>
);

/* Theme */
const ISun = (p) => (
  <VAIcon {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2" /><path d="M12 20v2" />
    <path d="m4.93 4.93 1.41 1.41" /><path d="m17.66 17.66 1.41 1.41" />
    <path d="M2 12h2" /><path d="M20 12h2" />
    <path d="m4.93 19.07 1.41-1.41" /><path d="m17.66 6.34 1.41-1.41" />
  </VAIcon>
);
const IMoon = (p) => (
  <VAIcon {...p}>
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />
  </VAIcon>
);
const IMonitor = (p) => (
  <VAIcon {...p}>
    <rect x="2" y="3" width="20" height="14" rx="2" />
    <path d="M8 21h8" />
    <path d="M12 17v4" />
  </VAIcon>
);

/* Chat / assistant */
const IMessage = (p) => (
  <VAIcon {...p}>
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </VAIcon>
);
const ISparkles = (p) => (
  <VAIcon {...p}>
    <path d="M9.94 14.34 12 21l2.06-6.66L21 12l-6.94-2.34L12 3l-2.06 6.66L3 12z" />
    <path d="M19 4v3" /><path d="M17.5 5.5h3" />
    <path d="M5 17v3" /><path d="M3.5 18.5h3" />
  </VAIcon>
);
const IMic = (p) => (
  <VAIcon {...p}>
    <rect x="9" y="2" width="6" height="12" rx="3" />
    <path d="M19 10a7 7 0 0 1-14 0" />
    <path d="M12 17v5" />
  </VAIcon>
);
const IPaperclip = (p) => (
  <VAIcon {...p}>
    <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66L9.41 17.41a2 2 0 1 1-2.83-2.83l8.49-8.49" />
  </VAIcon>
);

/* Status / signals */
const ICheck = (p) => (
  <VAIcon {...p}>
    <path d="M4 12.5 9 17.5l11-11" />
  </VAIcon>
);
const ICheckCircle = (p) => (
  <VAIcon {...p}>
    <circle cx="12" cy="12" r="10" />
    <path d="m8 12 3 3 5-6" />
  </VAIcon>
);
const IShield = (p) => (
  <VAIcon {...p}>
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
    <path d="m9 12 2 2 4-4" />
  </VAIcon>
);
const IAlert = (p) => (
  <VAIcon {...p}>
    <circle cx="12" cy="12" r="10" />
    <path d="M12 8v4" />
    <path d="M12 16h.01" />
  </VAIcon>
);
const IClock = (p) => (
  <VAIcon {...p}>
    <circle cx="12" cy="12" r="10" />
    <path d="M12 6v6l4 2" />
  </VAIcon>
);
const IEdit = (p) => (
  <VAIcon {...p}>
    <path d="M12 20h9" />
    <path d="M16.5 3.5a2.12 2.12 0 1 1 3 3L7 19l-4 1 1-4Z" />
  </VAIcon>
);
const IHelp = (p) => (
  <VAIcon {...p}>
    <circle cx="12" cy="12" r="10" />
    <path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 2-2.5 2-2.5 4" />
    <path d="M12 17h.01" />
  </VAIcon>
);
const IFile = (p) => (
  <VAIcon {...p}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <path d="M14 2v6h6" />
    <path d="M9 13h6" />
    <path d="M9 17h4" />
  </VAIcon>
);
const IGlobe = (p) => (
  <VAIcon {...p}>
    <circle cx="12" cy="12" r="10" />
    <path d="M2 12h20" />
    <path d="M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20Z" />
  </VAIcon>
);
const IDot = (p) => (
  <VAIcon {...p} strokeWidth={0}>
    <circle cx="12" cy="12" r="4" fill="currentColor" />
  </VAIcon>
);
const IRefresh = (p) => (
  <VAIcon {...p}>
    <path d="M3 12a9 9 0 0 1 15.5-6.4L21 8" />
    <path d="M21 3v5h-5" />
    <path d="M21 12a9 9 0 0 1-15.5 6.4L3 16" />
    <path d="M3 21v-5h5" />
  </VAIcon>
);
const ILogo = (p) => (
  /* Custom Voyage mark: a sun rising over a horizon line — used in chat avatar */
  <VAIcon {...p}>
    <path d="M3 17h18" />
    <path d="M12 5a7 7 0 0 1 7 7H5a7 7 0 0 1 7-7Z" fill="currentColor" stroke="none" />
  </VAIcon>
);
const IClose = (p) => (
  <VAIcon {...p}>
    <path d="m18 6-12 12" />
    <path d="m6 6 12 12" />
  </VAIcon>
);
const IMenu = (p) => (
  <VAIcon {...p}>
    <path d="M3 12h18" />
    <path d="M3 6h18" />
    <path d="M3 18h18" />
  </VAIcon>
);
const ITrash = (p) => (
  <VAIcon {...p}>
    <path d="M3 6h18" />
    <path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6" />
    <path d="M10 11v6" />
    <path d="M14 11v6" />
    <path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
  </VAIcon>
);

Object.assign(window, {
  IPlane, ITrain, IShip, IBus,
  ISearch, IMapPin, ICalendar, IUsers, ISwap,
  IArrowRight, IArrowLeft, IArrowUp, IChevronRight, IChevronDown,
  ISun, IMoon, IMonitor,
  IMessage, ISparkles, IMic, IPaperclip,
  ICheck, ICheckCircle, IShield, IAlert, IClock, IEdit, IHelp, IFile, IGlobe, IDot, IRefresh, ILogo, IClose, IMenu, ITrash,
});
