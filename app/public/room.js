const colors = {
  ink: "#101d2b",
  slate: "#273f4f",
  blue: "#94c9ee",
  brass: "#ddbb7a",
};
const looks = {
  dhh: [1, 1, 0, "#826340"],
  tobi: [0, 1, 1, "#161e28"],
  primeagen: [1, 0, 0, "#654438"],
  carmack: [1, 1, 0, "#b4aa83"],
  linus: [1, 1, 0, "#85877b"],
  ritchie: [1, 1, 0, "#b0a58b"],
  bjarne: [1, 1, 0, "#bcb6a1"],
  casey: [1, 0, 0, "#4b3931"],
  blow: [1, 0, 0, "#a7967a"],
  unclebob: [0, 1, 0, "#b4afa0"],
  vitalik: [1, 0, 0, "#594333"],
  dorsey: [1, 0, 0, "#4c3328"],
  zuckerberg: [1, 0, 0, "#936f4c"],
};
const short = {
  dhh: "DHH",
  tobi: "Tobi Lütke",
  primeagen: "ThePrimeagen",
  carmack: "John Carmack",
  linus: "Linus Torvalds",
  ritchie: "Dennis Ritchie",
  bjarne: "Bjarne Stroustrup",
  casey: "Casey Muratori",
  blow: "Jonathan Blow",
  unclebob: "Uncle Bob",
  vitalik: "Vitalik Buterin",
  dorsey: "Jack Dorsey",
  zuckerberg: "Mark Zuckerberg",
};
function fallbackLook(id) {
  let h = 0;
  for (const ch of String(id)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return [h % 2, (h >> 1) % 2, (h >> 2) % 2, "#" + (0x300000 + (h % 0x8f8f8f)).toString(16).padStart(6, "0")];
}
export class Room {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.seats = [];
    this.active = "";
    this.talking = false;
    this.reduced = matchMedia("(prefers-reduced-motion: reduce)");
    this.draw();
    this.timer = setInterval(() => {
      if (this.talking && !this.reduced.matches) this.draw();
    }, 320);
  }
  set(seats, active = "", talking = false) {
    this.seats = seats;
    this.active = active;
    this.talking = talking;
    this.draw();
  }
  draw() {
    const c = this.ctx;
    c.save();
    c.scale(2, 2);
    c.imageSmoothingEnabled = false;
    const r = (x, y, w, h, col) => {
      c.fillStyle = col;
      c.fillRect(Math.round(x), Math.round(y), w, h);
    };
    const line = (x, y, x2, y2, col) => {
      c.strokeStyle = col;
      c.lineWidth = 1;
      c.beginPath();
      c.moveTo(x, y);
      c.lineTo(x2, y2);
      c.stroke();
    };
    const text = (t, x, y, size = 5, col = "#94a9b4", maxWidth) => {
      c.fillStyle = col;
      c.font = `${size}px monospace`;
      c.textAlign = "center";
      c.fillText(t, x, y, maxWidth || 470);
    };
    r(0, 0, 480, 205, "#142a38");
    r(0, 0, 480, 9, "#10212e");
    r(12, 9, 456, 109, "#1b3443");
    for (let y = 116; y < 205; y += 12) {
      r(0, y, 480, 11, y % 24 === 20 ? "#443c34" : "#3d3832");
      for (let x = (y % 24) * 5 - 70; x < 480; x += 95)
        r(x, y, 1, 11, "#302d2a");
    }
    // Night window and distant city.
    r(145, 18, 190, 77, "#0a1b2d");
    r(148, 21, 184, 71, "#132d44");
    for (let i = 0; i < 25; i++) {
      let x = 151 + i * 7,
        h = 9 + ((i * 17) % 29);
      r(x, 84 - h, 5, h, "#1d3a4c");
      if (i % 3 === 0) r(x + 1, 81 - h, 1, 2, "#628497");
    }
    for (let i = 0; i < 22; i++)
      r(
        151 + ((i * 41) % 174),
        25 + ((i * 23) % 30),
        1,
        1,
        i % 3 ? "#4b708b" : "#b7c2ae",
      );
    r(300, 27, 9, 9, "#b6c4be");
    r(297, 25, 8, 8, "#132d44");
    r(145, 17, 190, 3, "#435967");
    r(145, 92, 190, 4, "#435967");
    r(145, 17, 3, 78, "#435967");
    r(332, 17, 3, 78, "#435967");
    r(239, 19, 3, 74, "#435967");
    r(143, 96, 194, 4, "#102634");
    // Books, terminals and a warm desk lamp.
    r(24, 28, 75, 72, "#10232e");
    for (let y = 33; y < 98; y += 21) {
      r(25, y + 16, 73, 3, "#526067");
      for (let x = 30; x < 90; x += 9) {
        r(
          x,
          y,
          6,
          15,
          ["#617c83", "#8f7753", "#3c5d70", "#92745e"][(x + y) % 4],
        );
        r(x + 2, y + 2, 2, 1, "#a7b4ac");
      }
    }
    r(360, 26, 80, 47, "#0b1d28");
    r(363, 29, 74, 40, "#102a36");
    for (let y = 34; y < 63; y += 5) {
      r(369, y, 14 + ((y * 13) % 39), 1, y % 2 ? "#71a7ad" : "#82958b");
    }
    r(396, 73, 5, 14, "#627276");
    r(381, 85, 35, 3, "#627276");
    line(449, 36, 452, 98, "#b1a080");
    r(440, 35, 18, 3, "#debc79");
    r(437, 38, 24, 5, "#c39b60");
    r(435, 43, 28, 4, "#ddbb7a");
    r(445, 98, 18, 3, "#8c7858");
    r(350, 103, 112, 8, "#79644a");
    r(354, 111, 5, 18, "#3b332d");
    r(451, 111, 5, 18, "#3b332d");
    text("D E N   O F   D E V S", 240, 108, 5, "#90a6ad");
    // Meeting table in perspective, understated blue edge light.
    c.fillStyle = "#242729";
    c.beginPath();
    c.moveTo(97, 129);
    c.lineTo(383, 129);
    c.lineTo(428, 181);
    c.lineTo(53, 181);
    c.closePath();
    c.fill();
    r(58, 179, 365, 6, "#2c3434");
    c.fillStyle = "#79664e";
    c.beginPath();
    c.moveTo(100, 124);
    c.lineTo(380, 124);
    c.lineTo(423, 177);
    c.lineTo(57, 177);
    c.closePath();
    c.fill();
    line(63, 174, 416, 174, "#ae9470");
    line(112, 130, 370, 130, "#8b775b");
    line(93, 150, 394, 150, "#6a5944");
    r(82, 183, 9, 22, "#1d2a2d");
    r(389, 183, 9, 22, "#1d2a2d");
    // Notebook, console, cups.
    r(212, 144, 51, 21, "#142b36");
    r(215, 147, 45, 15, "#1e3f4c");
    r(219, 150, 15, 1, "#94c9ee");
    r(219, 154, 29, 1, "#688e9b");
    r(210, 165, 55, 3, "#566b70");
    r(284, 152, 14, 16, "#d9d2b6");
    r(286, 155, 10, 1, "#9b9e94");
    r(173, 151, 8, 9, "#192b34");
    r(181, 153, 3, 4, "#192b34");
    const seats = this.seats.length
      ? this.seats
      : [
          { id: "carmack" },
          { id: "dhh" },
          { id: "tobi" },
          { id: "primeagen" },
          { id: "linus" },
        ];
    const points =
      seats.length === 1
        ? [[240, 115]]
        : seats.length === 5
        ? [
            [104, 118],
            [172, 116],
            [240, 115],
            [308, 116],
            [376, 118],
          ]
        : seats.map((_, i) => [
            65 + (i * 350) / (seats.length - 1),
            117 + Math.abs(i - (seats.length - 1) / 2) * 1.5,
          ]);
    seats.forEach((s, i) => {
      const [x, y] = points[i],
        a = s.id === this.active,
        [hair, glasses, cap, tone] = looks[s.id] || fallbackLook(s.id);
      r(x - 14, y - 5, 28, 29, "#16242e");
      r(x - 17, y - 2, 3, 25, "#0d1b26");
      r(x + 14, y - 2, 3, 25, "#0d1b26");
      r(x - 12, y - 13, 24, 22, a ? "#466172" : "#2d4655");
      r(x - 15, y - 8, 5, 16, "#334b58");
      r(x + 10, y - 8, 5, 16, "#334b58");
      r(x - 10, y + 7, 20, 4, "#243843");
      r(x - 4, y - 20, 8, 8, "#c39a7e");
      r(x - 9, y - 39, 18, 21, "#d3ac90");
      r(x - 11, y - 33, 3, 8, "#c49c80");
      r(x + 8, y - 33, 3, 8, "#c49c80");
      r(x - 7, y - 40, 14, 4, tone);
      if (hair) {
        r(x - 9, y - 38, 3, 9, tone);
        r(x + 6, y - 38, 3, 9, tone);
        r(x - 6, y - 42, 11, 3, tone);
      }
      if (s.id === "dorsey" || s.id === "primeagen")
        r(x - 7, y - 24, 14, 10, tone);
      r(x - 5, y - 30, 2, 2, "#172735");
      r(x + 3, y - 30, 2, 2, "#172735");
      if (glasses) {
        r(x - 8, y - 32, 7, 1, "#1e2e35");
        r(x + 1, y - 32, 7, 1, "#1e2e35");
        r(x - 8, y - 31, 1, 4, "#1e2e35");
        r(x + 7, y - 31, 1, 4, "#1e2e35");
        r(x - 1, y - 30, 2, 1, "#1e2e35");
      }
      if (cap) {
        r(x - 10, y - 42, 20, 7, "#111e27");
        r(x - 3, y - 35, 17, 2, "#111e27");
        r(x - 2, y - 40, 4, 3, "#c9c9b1");
      }
      r(
        x - 2,
        y - 23,
        5,
        a && this.talking && !this.reduced.matches && Date.now() % 640 < 320
          ? 3
          : 1,
        "#744b40",
      );
      r(x - 13, y + 4, 8, 4, "#c9a58b");
      r(x + 5, y + 4, 8, 4, "#c9a58b");
      r(x - 28, y + 15, 56, 10, a ? "#35576b" : "#172c38");
      if (a) r(x - 28, y + 24, 56, 1, colors.brass);
      text((short[s.id] || s.name || s.id), x, y + 22, 5.1, a ? "#f0d8aa" : "#b5c6cd", Math.min(52,380/seats.length));
    });
    // Foreground plant, stacked books and ambient grain.
    r(8, 176, 16, 25, "#293c3b");
    r(5, 170, 22, 7, "#77654d");
    r(14, 147, 3, 24, "#536d59");
    r(5, 151, 10, 7, "#587967");
    r(17, 146, 13, 6, "#6b8870");
    r(18, 157, 10, 6, "#4a705f");
    r(447, 183, 27, 5, "#768087");
    r(450, 177, 24, 5, "#937c60");
    r(444, 189, 30, 6, "#314b5b");
    c.restore();
  }
}
