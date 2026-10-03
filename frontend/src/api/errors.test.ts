import { AppError, errorFromResponse } from "@/api/errors";

describe("errorFromResponse", () => {
  it("keeps a domain message as it is", () => {
    const error = errorFromResponse(404, { detail: "Trace 7 not found" });

    expect(error).toBeInstanceOf(AppError);
    expect(error.kind).toBe("http");
    expect(error.status).toBe(404);
    expect(error.message).toBe("Trace 7 not found");
  });

  it("turns FastAPI validation details into field errors", () => {
    const error = errorFromResponse(422, {
      detail: [
        { loc: ["body", "entrypoint_model"], msg: "Field required", type: "missing" },
        { loc: ["query", "limit"], msg: "Input should be less than or equal to 200", type: "le" },
      ],
    });

    expect(error.kind).toBe("validation");
    expect(error.fieldErrors).toEqual([
      { path: "body.entrypoint_model", message: "Field required" },
      { path: "query.limit", message: "Input should be less than or equal to 200" },
    ]);
    expect(error.message).toBe(
      "body.entrypoint_model: Field required; query.limit: Input should be less than or equal to 200",
    );
  });

  it("treats a 422 with a plain message as validation", () => {
    expect(errorFromResponse(422, { detail: "bad call" }).kind).toBe("validation");
  });

  it.each([undefined, "<html>Bad Gateway</html>", { error: "x" }, { detail: [1, 2] }])(
    "falls back to unexpected for an unreadable body (%s)",
    (body) => {
      const error = errorFromResponse(502, body);

      expect(error.kind).toBe("unexpected");
      expect(error.message).toBe("The API answered with HTTP 502.");
    },
  );
});
