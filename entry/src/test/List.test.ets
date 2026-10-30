import engineTest from './Engine.test';
import validatorTest from './Validator.test';
import codecTest from './Codec.test';

export default function testsuite() {
  engineTest();
  validatorTest();
  codecTest();
}
