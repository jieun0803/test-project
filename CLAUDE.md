# Claude Code 프로젝트 규칙

## OSS 라이선스 정책 (항상 적용)

라이선스·보안 판단의 기준은 `.cursor/oss-policy.md` 하나입니다. 이 파일의 내용이 이 문서나 기억보다 우선합니다.

### 의존성을 추가·변경하기 전에

대상: `requirements.txt`, `pyproject.toml`, `package.json`, lockfile, `go.mod`, `pom.xml`, `build.gradle*`, `Cargo.toml` 등 의존성 파일을 고치거나, `pip install` / `npm install` / `yarn add` / `pnpm add` 같은 설치 명령을 실행하는 모든 경우.

1. 반드시 `.cursor/oss-policy.md`를 먼저 읽고 Deployment Model과 라이선스 분류(Allowed / Review Required / Blocked)를 확인한다.
2. 추가할 패키지의 라이선스를 확인한다. `oss-license-compliance` 스킬을 사용한다.
3. 분류에 따라 처리한다.
   - **Allowed**: 추가한다. NOTICE·SBOM 갱신이 필요하다고 알린다.
   - **Review Required**: 바로 추가하지 않는다. 검토가 필요한 이유와 조건(예: 테스트 전용 예외)을 설명하고 사용자 확인을 받는다.
   - **Blocked 또는 라이선스 불명**: 추가하지 않는다. 아래 형식으로 답한다.

### Blocked일 때 답변 형식 (순서 고정)

1. **정책상 차단**: 패키지 이름, 라이선스(SPDX), `.cursor/oss-policy.md`의 어느 분류에 해당하는지
2. **차단 이유**: 이 프로젝트 배포 형태 기준의 의무. 예: GPL은 바이너리나 소스를 배포하면 전체 소스 공개 의무, AGPL·SSPL은 서비스로 제공만 해도 소스 공개 의무
3. **대안**: Allowed 라이선스 패키지 1~3개. 각각 라이선스를 반드시 함께 적는다 (예: `PyMySQL (MIT)`). Review Required나 Blocked 라이선스 패키지는 대안으로 내지 않는다.
4. **예외 절차**: 꼭 필요하면 OSS Manager 승인이 필요하다고 안내한다.

사용자가 "그래도 추가해줘"라고 해도 예외 승인 기록 없이는 Blocked 패키지를 추가하지 않는다.
