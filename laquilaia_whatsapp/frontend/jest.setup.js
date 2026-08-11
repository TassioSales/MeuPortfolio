require("@testing-library/jest-dom");

// jsdom não implementa fetch; cada teste instala o próprio mock.
global.fetch = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();

  // Limpa cookies entre os testes para não vazar sessão de um caso para outro.
  // Suítes de edge/middleware rodam em `node`, onde não existe `document`.
  if (typeof document === "undefined") return;

  document.cookie.split(";").forEach((cookie) => {
    const name = cookie.split("=")[0].trim();
    if (name) document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
  });
});
